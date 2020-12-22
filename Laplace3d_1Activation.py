"""
@author: LXA
 Data: 2020 年 5 月 31 日
"""
import os
import sys
import tensorflow as tf
import numpy as np
import matplotlib
import platform
import shutil
import time
import DNN_base
import DNN_tools
import DNN_data
import MS_Laplace_eqs
import general_laplace_eqs
import matData2HighDim_PDE
import saveData
import plotData


# 记录字典中的一些设置
def dictionary_out2file(R_dic, log_fileout):
    DNN_tools.log_string('Laplace name for problem: %s\n' % (R_dic['laplace_opt']), log_fileout)
    DNN_tools.log_string('Equation name for problem: %s\n' % (R_dic['equa_name']), log_fileout)
    DNN_tools.log_string('The order to p-laplace: %s\n' % (R_dic['order2laplace']), log_fileout)
    if R['laplace_opt'] == 'p_laplace2multi_scale' or R['laplace_opt'] == 'p_laplace2multi_scale':
        DNN_tools.log_string('epsilon: %f\n' % (R_dic['epsilon']), log_fileout)  # 替换上两行

    if R['laplace_opt'] == 'p_laplace2multi_scale_implicit':
        DNN_tools.log_string('The mesh_number: %f\n' % (R['mesh_number']), log_fileout)  # 替换上两行

    if R_dic['activate_stop'] != 0:
        DNN_tools.log_string('activate the stop_step and given_step= %s\n' % str(R_dic['max_epoch']), log_fileout)
    else:
        DNN_tools.log_string('no activate the stop_step and given_step = default: %s\n' % str(R_dic['max_epoch']), log_fileout)

    if R_dic['variational_loss'] == 1:
        DNN_tools.log_string('Loss function: variational loss\n', log_fileout)
    else:
        DNN_tools.log_string('Loss function: original function loss\n', log_fileout)

    DNN_tools.log_string('Network model of solving problem: %s\n' % str(R_dic['model']), log_fileout)
    DNN_tools.log_string('The frequency flags to Network: %s\n' % (R_dic['freqs']), log_fileout)
    DNN_tools.log_string('Activate function for network: %s\n' % str(R_dic['activate_func']), log_fileout)

    if (R_dic['optimizer_name']).title() == 'Adam':
        DNN_tools.log_string('optimizer:%s\n' % str(R_dic['optimizer_name']), log_fileout)
    else:
        DNN_tools.log_string('optimizer:%s  with momentum=%f\n' % (R_dic['optimizer_name'], R_dic['momentum']), log_fileout)

    DNN_tools.log_string('Init learning rate: %s\n' % str(R_dic['learning_rate']), log_fileout)

    DNN_tools.log_string('Decay to learning rate: %s\n' % str(R_dic['learning_rate_decay']), log_fileout)

    DNN_tools.log_string('hidden layer:%s\n' % str(R_dic['hidden_layers']), log_fileout)

    DNN_tools.log_string('Batch-size 2 interior: %s\n' % str(R_dic['batch_size2interior']), log_fileout)
    DNN_tools.log_string('Batch-size 2 boundary: %s\n' % str(R_dic['batch_size2boundary']), log_fileout)

    DNN_tools.log_string('Initial boundary penalty: %s\n' % str(R_dic['init_boundary_penalty']), log_fileout)
    if R['activate_penalty2bd_increase'] == 1:
        DNN_tools.log_string('The penalty of boundary will increase with training going on.\n', log_fileout)
    elif R['activate_penalty2bd_increase'] == 2:
        DNN_tools.log_string('The penalty of boundary will decrease with training going on.\n', log_fileout)
    else:
        DNN_tools.log_string('The penalty of boundary will keep unchanged with training going on.\n', log_fileout)


def solve_laplace(R):
    log_out_path = R['FolderName']        # 将路径从字典 R 中提取出来
    if not os.path.exists(log_out_path):  # 判断路径是否已经存在
        os.mkdir(log_out_path)            # 无 log_out_path 路径，创建一个 log_out_path 路径
    logfile_name = '%s%s.txt' % ('log2', R['activate_func'])
    log_fileout = open(os.path.join(log_out_path, logfile_name), 'w')  # 在这个路径下创建并打开一个可写的 log_train.txt文件
    dictionary_out2file(R, log_fileout)

    # 一般 laplace 问题需要的设置
    batchsize_it = R['batch_size2interior']
    batchsize_bd = R['batch_size2boundary']

    bd_penalty_init = R['init_boundary_penalty']                # Regularization parameter for boundary conditions
    wb_regular = R['regular_weight_biases']                # Regularization parameter for weights and biases
    lr_decay = R['learning_rate_decay']
    learning_rate = R['learning_rate']
    hidden_layers = R['hidden_layers']
    act_func = R['activate_func']

    input_dim = R['input_dim']
    out_dim = R['output_dim']

    # p laplace 问题需要的额外设置, 先预设一下
    p = 2
    mesh_number = 2

    region_lb = 0.0
    region_rt = 1.0
    if R['laplace_opt'] == 'general_laplace':
        # -laplace u = f
        region_lb = 0.0
        region_rt = 1.0
        f, u_true, u_left, u_right, u_bottom, u_top = general_laplace_eqs.get_general_laplace_infos(
            input_dim=input_dim, out_dim=out_dim, left_bottom=region_lb, right_top=region_rt, laplace_name=R['equa_name'])
    elif R['laplace_opt'] == 'p_laplace2multi_scale':
        region_lb = 0.0
        region_rt = 1.0
        u_true, f, A_eps = MS_Laplace_eqs.get_laplace_multi_scale_infos3D(
            input_dim=input_dim, out_dim=out_dim, mesh_number=R['mesh_number'], region_lb=0.0, region_rt=1.0,
            laplace_name=R['equa_name'])

    flag = 'WB2NN'
    # Weights, Biases = PDE_DNN_base.Initial_DNN2different_hidden(input_dim, out_dim, hidden_layers, flag)
    # Weights, Biases = DNN_base.initialize_NN_xavier(input_dim, out_dim, hidden_layers, flag1)
    # Weights, Biases = DNN_base.initialize_NN_random_normal(input_dim, out_dim, hidden_layers, flag1)
    W2NN, B2NN = DNN_base.initialize_NN_random_normal2(input_dim, out_dim, hidden_layers, flag)

    global_steps = tf.Variable(0, trainable=False)
    with tf.device('/gpu:%s' % (R['gpuNo'])):
        with tf.variable_scope('vscope', reuse=tf.AUTO_REUSE):
            XYZ_it = tf.placeholder(tf.float32, name='XYZ_it', shape=[None, input_dim])
            XYZ_bottom_bd = tf.placeholder(tf.float32, name='bottom_bd', shape=[None, input_dim])
            XYZ_top_bd = tf.placeholder(tf.float32, name='top_bd', shape=[None, input_dim])
            XYZ_left_bd = tf.placeholder(tf.float32, name='left_bd', shape=[None, input_dim])
            XYZ_right_bd = tf.placeholder(tf.float32, name='right_bd', shape=[None, input_dim])
            XYZ_front_bd = tf.placeholder(tf.float32, name='front_bd', shape=[None, input_dim])
            XYZ_behind_bd = tf.placeholder(tf.float32, name='behind_bd', shape=[None, input_dim])
            boundary_penalty = tf.placeholder_with_default(input=1e3, shape=[], name='bd_p')
            in_learning_rate = tf.placeholder_with_default(input=1e-5, shape=[], name='lr')
            train_opt = tf.placeholder_with_default(input=True, shape=[], name='train_opt')

            # 供选择的网络模式
            if R['model'] == 'PDE_DNN':
                U_NN = DNN_base.PDE_DNN(XYZ_it, W2NN, B2NN, hidden_layers, activate_name=act_func)
                ULeft_NN = DNN_base.PDE_DNN(XYZ_left_bd, W2NN, B2NN, hidden_layers, activate_name=act_func)
                URight_NN = DNN_base.PDE_DNN(XYZ_right_bd, W2NN, B2NN, hidden_layers, activate_name=act_func)
                UBottom_NN = DNN_base.PDE_DNN(XYZ_bottom_bd, W2NN, B2NN, hidden_layers, activate_name=act_func)
                UTop_NN = DNN_base.PDE_DNN(XYZ_top_bd, W2NN, B2NN, hidden_layers, activate_name=act_func)
                UFront_NN = DNN_base.PDE_DNN(XYZ_front_bd, W2NN, B2NN, hidden_layers, activate_name=act_func)
                UBehind_NN = DNN_base.PDE_DNN(XYZ_behind_bd, W2NN, B2NN, hidden_layers, activate_name=act_func)
            elif R['model'] == 'PDE_DNN_scale':
                freqs = R['freqs']
                U_NN = DNN_base.PDE_DNN_scale(XYZ_it, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                ULeft_NN = DNN_base.PDE_DNN_scale(XYZ_left_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                URight_NN = DNN_base.PDE_DNN_scale(XYZ_right_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UBottom_NN = DNN_base.PDE_DNN_scale(XYZ_bottom_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UTop_NN = DNN_base.PDE_DNN_scale(XYZ_top_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UFront_NN = DNN_base.PDE_DNN_scale(XYZ_front_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UBehind_NN = DNN_base.PDE_DNN_scale(XYZ_behind_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
            elif R['model'] == 'PDE_DNN_adapt_scale':
                freqs = R['freqs']
                U_NN = DNN_base.PDE_DNN_adapt_scale(XYZ_it, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                ULeft_NN = DNN_base.PDE_DNN_adapt_scale(XYZ_left_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                URight_NN = DNN_base.PDE_DNN_adapt_scale(XYZ_right_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UBottom_NN = DNN_base.PDE_DNN_adapt_scale(XYZ_bottom_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UTop_NN = DNN_base.PDE_DNN_adapt_scale(XYZ_top_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UFront_NN = DNN_base.PDE_DNN_adapt_scale(XYZ_front_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UBehind_NN = DNN_base.PDE_DNN_adapt_scale(XYZ_behind_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
            elif R['model'] == 'PDE_DNN_FourierBase':
                freqs = R['freqs']
                U_NN = DNN_base.PDE_DNN_FourierBase(XYZ_it, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                ULeft_NN = DNN_base.PDE_DNN_FourierBase(XYZ_left_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                URight_NN = DNN_base.PDE_DNN_FourierBase(XYZ_right_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UBottom_NN = DNN_base.PDE_DNN_FourierBase(XYZ_bottom_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UTop_NN = DNN_base.PDE_DNN_FourierBase(XYZ_top_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UFront_NN = DNN_base.PDE_DNN_FourierBase(XYZ_front_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)
                UBehind_NN = DNN_base.PDE_DNN_FourierBase(XYZ_behind_bd, W2NN, B2NN, hidden_layers, freqs, activate_name=act_func)

            X_it = tf.reshape(XYZ_it[:, 0], shape=[-1, 1])
            Y_it = tf.reshape(XYZ_it[:, 1], shape=[-1, 1])
            Z_it = tf.reshape(XYZ_it[:, 2], shape=[-1, 1])
            # 变分形式的loss of interior，训练得到的 U_NN 是 * 行 1 列, 因为 一个点对(x,y) 得到一个 u 值
            if R['variational_loss'] == 1:
                dU_NN = tf.gradients(U_NN, XYZ_it)[0]      # * 行 2 列
                dU_NN_2norm = tf.reshape(tf.sqrt(tf.reduce_sum(tf.square(dU_NN), axis=-1)), shape=[-1, 1])  # 按行求和
                if R['laplace_opt'] == 'general_laplace':
                    laplace_pow = tf.square(dU_NN_2norm)
                    loss_it_variational = (1.0 / 2) *laplace_pow - tf.multiply(f(X_it, Y_it, Z_it), U_NN)
                else:
                    a_eps = A_eps(X_it, Y_it, Z_it)                          # * 行 1 列
                    laplace_p_pow = a_eps*tf.pow(dU_NN_2norm, p)
                    loss_it_variational = (1.0 / p) * laplace_p_pow - tf.multiply(f(X_it, Y_it, Z_it), U_NN)
                loss_it = tf.reduce_mean(loss_it_variational)*(region_rt-region_lb)*(region_rt-region_lb)

                U_left = tf.constant(0.0)
                U_right = tf.constant(0.0)
                U_bottom = tf.constant(0.0)
                U_top = tf.constant(0.0)
                U_front = tf.constant(0.0)
                U_behind = tf.constant(0.0)

                loss_bd_square = tf.square(ULeft_NN - U_left) + tf.square(URight_NN - U_right) + \
                                 tf.square(UBottom_NN - U_bottom) + tf.square(UTop_NN - U_top) + \
                                 tf.square(UFront_NN - U_front) + tf.square(UBehind_NN - U_behind)
                loss_bd = tf.reduce_mean(loss_bd_square)

            if R['regular_weight_model'] == 'L1':
                regular_WB = DNN_base.regular_weights_biases_L1(W2NN, B2NN)    # 正则化权重和偏置 L1正则化
            elif R['regular_weight_model'] == 'L2':
                regular_WB = DNN_base.regular_weights_biases_L2(W2NN, B2NN)    # 正则化权重和偏置 L2正则化
            else:
                regular_WB = tf.constant(0.0)                                        # 无正则化权重参数

            penalty_WB = wb_regular * regular_WB
            loss = loss_it + boundary_penalty * loss_bd + wb_regular * regular_WB       # 要优化的loss function

            my_optimizer = tf.train.AdamOptimizer(in_learning_rate)
            if R['train_group'] == 1:
                train_op2bd = my_optimizer.minimize(loss_bd, global_step=global_steps)
                train_op2union = my_optimizer.minimize(loss, global_step=global_steps)
                train_my_loss = tf.gruop(train_op2union, train_op2bd)
            else:
                train_my_loss = my_optimizer.minimize(loss, global_step=global_steps)

            if R['laplace_opt'] == 'general_laplace' or R['laplace_opt'] == 'p_laplace2multi_scale':
                # 训练上的真解值和训练结果的误差
                U_true = u_true(X_it, Y_it, Z_it)
                train_mse = tf.reduce_mean(tf.square(U_true - U_NN))
                train_rel = train_mse / tf.reduce_mean(tf.square(U_true))

                # dU_true = tf.gradients(U_true, XYZ_it)[0]
                # dU_true_2norm = tf.reshape(tf.sqrt(tf.reduce_sum(tf.square(dU_true), axis=-1)), shape=[-1, 1])  # 按行求和
                # a_eps2 = A_eps(X_it, Y_it, Z_it)  # * 行 1 列
                # laplace_Utrue = a_eps2 * tf.pow(dU_true_2norm, p)
                # loss_it_Utrue= (1.0 / p) * laplace_Utrue - tf.multiply(f(X_it, Y_it, Z_it), U_true)
                # loss_it2Utrue = tf.reduce_mean(loss_it_Utrue) * (region_rt - region_lb) * (region_rt - region_lb)
            else:
                train_mse = tf.constant(0.0)
                train_rel = tf.constant(0.0)

    t0 = time.time()
    loss_it_all, loss_bd_all, loss_all, train_mse_all, train_rel_all = [], [], [], [], []  # 空列表, 使用 append() 添加元素
    test_mse_all, test_rel_all = [], []
    test_epoch = []

    # 画网格解图
    if R['testData_model'] == 'random_generate':
        # 生成测试数据，用于测试训练后的网络
        # test_bach_size = 400
        # size2test = 20
        # test_bach_size = 900
        # size2test = 30
        test_bach_size = 1600
        size2test = 40
        # test_bach_size = 4900
        # size2test = 70
        # test_bach_size = 10000
        # size2test = 100
        # test_bach_size = 40000
        # size2test = 200
        # test_bach_size = 250000
        # size2test = 500
        # test_bach_size = 1000000
        # size2test = 1000
        test_xyz_bach = DNN_data.rand_it(test_bach_size, input_dim, region_lb, region_rt)
        saveData.save_testData_or_solus2mat(test_xyz_bach, dataName='testXYZ', outPath=R['FolderName'])
    elif R['testData_model'] == 'loadData':
        test_bach_size = 1600
        size2test = 40
        mat_data_path = 'data2mat'
        test_xyz_bach = matData2HighDim_PDE.get_data2Biharmonic(dim=input_dim, data_path=mat_data_path)
        saveData.save_testData_or_solus2mat(test_xyz_bach, dataName='testXYZ', outPath=R['FolderName'])

    # ConfigProto 加上allow_soft_placement=True就可以使用 gpu 了
    config = tf.ConfigProto(allow_soft_placement=True)  # 创建sess的时候对sess进行参数配置
    config.gpu_options.allow_growth = True              # True是让TensorFlow在运行过程中动态申请显存，避免过多的显存占用。
    config.allow_soft_placement = True                  # 当指定的设备不存在时，允许选择一个存在的设备运行。比如gpu不存在，自动降到cpu上运行
    with tf.Session(config=config) as sess:
        sess.run(tf.global_variables_initializer())
        tmp_lr = learning_rate

        train_option = True
        for i_epoch in range(R['max_epoch'] + 1):
            xyz_it_batch = DNN_data.rand_it(batchsize_it, input_dim, region_a=region_lb, region_b=region_rt)
            xyz_bottom_batch, xyz_top_batch, xyz_left_batch, xyz_right_batch, xyz_front_batch, xyz_behind_batch = \
                DNN_data.rand_bd_3D(batchsize_bd, input_dim, region_a=region_lb, region_b=region_rt)
            tmp_lr = tmp_lr * (1 - lr_decay)
            if R['activate_penalty2bd_increase'] == 1:
                if i_epoch < int(R['max_epoch'] / 10):
                    temp_penalty_bd = bd_penalty_init
                elif i_epoch < int(R['max_epoch'] / 5):
                    temp_penalty_bd = 10 * bd_penalty_init
                elif i_epoch < int(R['max_epoch'] / 4):
                    temp_penalty_bd = 50 * bd_penalty_init
                elif i_epoch < int(R['max_epoch'] / 2):
                    temp_penalty_bd = 100 * bd_penalty_init
                elif i_epoch < int(3 * R['max_epoch'] / 4):
                    temp_penalty_bd = 200 * bd_penalty_init
                else:
                    temp_penalty_bd = 500 * bd_penalty_init
            elif R['activate_penalty2bd_increase'] == 2:
                if i_epoch < int(R['max_epoch'] / 10):
                    temp_penalty_bd = 5*bd_penalty_init
                elif i_epoch < int(R['max_epoch'] / 5):
                    temp_penalty_bd = 1 * bd_penalty_init
                elif i_epoch < int(R['max_epoch'] / 4):
                    temp_penalty_bd = 0.5 * bd_penalty_init
                elif i_epoch < int(R['max_epoch'] / 2):
                    temp_penalty_bd = 0.1 * bd_penalty_init
                elif i_epoch < int(3 * R['max_epoch'] / 4):
                    temp_penalty_bd = 0.05 * bd_penalty_init
                else:
                    temp_penalty_bd = 0.02 * bd_penalty_init
            else:
                temp_penalty_bd = bd_penalty_init

            _, loss_it_tmp, loss_bd_tmp, loss_tmp, train_mse_tmp, train_res_tmp, p_WB = sess.run(
                [train_my_loss, loss_it, loss_bd, loss, train_mse, train_rel, penalty_WB],
                feed_dict={XYZ_it: xyz_it_batch, XYZ_left_bd: xyz_left_batch, XYZ_right_bd: xyz_right_batch,
                           XYZ_bottom_bd: xyz_bottom_batch, XYZ_top_bd: xyz_top_batch, XYZ_front_bd: xyz_front_batch,
                           XYZ_behind_bd: xyz_behind_batch, in_learning_rate: tmp_lr,
                           boundary_penalty: temp_penalty_bd, train_opt: train_option})

            loss_it_all.append(loss_it_tmp)
            loss_bd_all.append(loss_bd_tmp)
            loss_all.append(loss_tmp)
            train_mse_all.append(train_mse_tmp)
            train_rel_all.append(train_res_tmp)

            if i_epoch % 1000 == 0:
                run_times = time.time() - t0
                DNN_tools.print_and_log_train_one_epoch(
                    i_epoch, run_times, tmp_lr, temp_penalty_bd, p_WB, loss_it_tmp, loss_bd_tmp, loss_tmp, train_mse_tmp,
                    train_res_tmp, log_out=log_fileout)

                # ---------------------------   test network ----------------------------------------------
                test_epoch.append(i_epoch / 1000)
                train_option = False
                if R['laplace_opt'] == 'general_laplace' or R['laplace_opt'] == 'p_laplace2multi_scale':
                    u_true2test, u_nn2test, lossIt2uprect = sess.run(
                        [U_true, U_NN, loss_it], feed_dict={XYZ_it: test_xyz_bach, train_opt: train_option})
                else:
                    u_true2test = u_true
                    u_nn2test, lossIt2uprect = sess.run(
                        [U_NN, loss_it],  feed_dict={XYZ_it: test_xyz_bach, train_opt: train_option})

                point_square_error = np.square(u_true2test - u_nn2test)
                mse2test = np.mean(point_square_error)
                test_mse_all.append(mse2test)
                res2test = mse2test / np.mean(np.square(u_true2test))
                test_rel_all.append(res2test)

                DNN_tools.print_and_log_test_one_epoch(mse2test, res2test, log_out=log_fileout)

        # ------------------- save the testing results into mat file and plot them -------------------------
        saveData.save_trainLoss2mat_1actFunc(loss_it_all, loss_bd_all, loss_all, actName=act_func,
                                             outPath=R['FolderName'])
        saveData.save_train_MSE_REL2mat(train_mse_all, train_rel_all, actName=act_func, outPath=R['FolderName'])

        plotData.plotTrain_loss_1act_func(loss_it_all, lossType='loss_it', seedNo=R['seed'], outPath=R['FolderName'])
        plotData.plotTrain_loss_1act_func(loss_bd_all, lossType='loss_bd', seedNo=R['seed'], outPath=R['FolderName'],
                                          yaxis_scale=True)
        plotData.plotTrain_loss_1act_func(loss_all, lossType='loss', seedNo=R['seed'], outPath=R['FolderName'])

        saveData.save_train_MSE_REL2mat(train_mse_all, train_rel_all, actName=act_func, outPath=R['FolderName'])
        plotData.plotTrain_MSE_REL_1act_func(train_mse_all, train_rel_all, actName=act_func, seedNo=R['seed'],
                                             outPath=R['FolderName'], yaxis_scale=True)

        # ----------------------  save testing results to mat files, then plot them --------------------------------
        saveData.save_2testSolus2mat(u_true2test, u_nn2test, actName='utrue', actName1=act_func, outPath=R['FolderName'])
        if R['hot_power'] == 1:
            # ----------------------------------------------------------------------------------------------------------
            #                                      绘制解的热力图(真解和DNN解)
            # ----------------------------------------------------------------------------------------------------------
            plotData.plot_Hot_solution2test(u_true2test, size_vec2mat=size2test, actName='Utrue', seedNo=R['seed'],
                                            outPath=R['FolderName'])
            plotData.plot_Hot_solution2test(u_nn2test, size_vec2mat=size2test, actName=act_func, seedNo=R['seed'],
                                            outPath=R['FolderName'])

        saveData.save_testMSE_REL2mat(test_mse_all, test_rel_all, actName=act_func, outPath=R['FolderName'])
        plotData.plotTest_MSE_REL(test_mse_all, test_rel_all, test_epoch, actName=act_func,
                                  seedNo=R['seed'], outPath=R['FolderName'], yaxis_scale=True)

        saveData.save_test_point_wise_err2mat(point_square_error, actName=act_func, outPath=R['FolderName'])

        plotData.plot_Hot_point_wise_err(point_square_error, size_vec2mat=size2test, actName=act_func,
                                         seedNo=R['seed'], outPath=R['FolderName'])


if __name__ == "__main__":
    R={}
    # -------------------------------------- CPU or GPU 选择 -----------------------------------------------
    R['gpuNo'] = 0
    # 默认使用 GPU，这个标记就不要设为-1，设为0,1,2,3,4....n（n指GPU的数目，即电脑有多少块GPU）
    # os.environ["CUDA_VISIBLE_DEVICES"] = "-1" # -1代表使用 CPU 模式
    # os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # 设置当前使用的GPU设备仅为第 0 块GPU, 设备名称为'/gpu:0'
    if platform.system() == 'Windows':
        os.environ["CDUA_VISIBLE_DEVICES"] = "%s" % (R['gpuNo'])
    else:
        print('-------------------------------------- linux -----------------------------------------------')
        # Linux终端没有GUI, 需要添加如下代码，而且必须添加在 import matplotlib.pyplot 之前，否则无效。
        matplotlib.use('Agg')

        if tf.test.is_gpu_available():
            os.environ["CUDA_VISIBLE_DEVICES"] = "0,1,2,3"  # 设置当前使用的GPU设备仅为第 0,1,2,3 块GPU, 设备名称为'/gpu:0'
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = "1"

    # 文件保存路径设置
    store_file = 'laplace3d'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(BASE_DIR)
    OUT_DIR = os.path.join(BASE_DIR, store_file)
    if not os.path.exists(OUT_DIR):
        print('---------------------- OUT_DIR ---------------------:', OUT_DIR)
        os.mkdir(OUT_DIR)

    R['seed'] = np.random.randint(1e5)
    seed_str = str(R['seed'])                     # int 型转为字符串型
    FolderName = os.path.join(OUT_DIR, seed_str)  # 路径连接
    R['FolderName'] = FolderName
    if not os.path.exists(FolderName):
        print('--------------------- FolderName -----------------:', FolderName)
        os.mkdir(FolderName)

    # ----------------------------------------  复制并保存当前文件 -----------------------------------------
    if platform.system() == 'Windows':
        tf.compat.v1.reset_default_graph()
        shutil.copy(__file__, '%s/%s' % (FolderName, os.path.basename(__file__)))
    else:
        shutil.copy(__file__, '%s/%s' % (FolderName, os.path.basename(__file__)))

    # if the value of step_stop_flag is not 0, it will activate stop condition of step to kill program
    step_stop_flag = input('please input an  integer number to activate step-stop----0:no---!0:yes--:')
    R['activate_stop'] = int(step_stop_flag)
    # if the value of step_stop_flag is not 0, it will activate stop condition of step to kill program
    R['max_epoch'] = 200000
    if 0 != R['activate_stop']:
        epoch_stop = input('please input a stop epoch:')
        R['max_epoch'] = int(epoch_stop)

    # ---------------------------- Setup of multi-scale problem-------------------------------
    R['input_dim'] = 3  # 输入维数，即问题的维数(几元问题)
    R['output_dim'] = 1  # 输出维数

    # R['laplace_opt'] = 'general_laplace'
    # R['equa_name'] = 'PDE1'
    # R['equa_name'] = 'PDE2'
    # R['equa_name'] = 'PDE3'
    # R['equa_name'] = 'PDE4'
    # R['equa_name'] = 'PDE5'
    # R['equa_name'] = 'PDE6'
    # R['equa_name'] = 'PDE7'

    R['laplace_opt'] = 'p_laplace2multi_scale'
    # R['equa_name'] = 'multi_scale3D_1'
    R['equa_name'] = 'multi_scale3D_2'

    if R['laplace_opt'] == 'general_laplace':
        R['mesh_number'] = 1
        R['epsilon'] = 0.1
        R['order2laplace'] = 2
        R['batch_size2interior'] = 5000  # 内部训练数据的批大小
        R['batch_size2boundary'] = 1000
    elif R['laplace_opt'] == 'p_laplace2multi_scale':
        R['mesh_number'] = 1
        R['epsilon'] = 0.1
        R['order2laplace'] = 2
        R['batch_size2interior'] = 5000  # 内部训练数据的批大小
        R['batch_size2boundary'] = 1000

    # ---------------------------- Setup of DNN -------------------------------
    # 装载测试数据模式和画图模式
    R['hot_power'] = 1
    R['testData_model'] = 'loadData'

    R['variational_loss'] = 1  # PDE变分

    R['optimizer_name'] = 'Adam'  # 优化器
    R['learning_rate'] = 2e-4  # 学习率
    R['learning_rate_decay'] = 5e-5  # 学习率 decay
    R['train_group'] = 0

    R['weight_biases_model'] = 'general_model'              # 权重和偏置生成模式
    # 正则化权重和偏置的模式
    R['regular_weight_model'] = 'L0'
    # R['regular_weight_model'] = 'L1'
    # R['regular_weight_model'] = 'L2'
    R['regular_weight_biases'] = 0.000                      # Regularization parameter for weights
    # R['regular_weight_biases'] = 0.001                    # Regularization parameter for weights
    # R['regular_weight_biases'] = 0.0025                   # Regularization parameter for weights

    # 边界的惩罚处理方式,以及边界的惩罚因子
    R['activate_penalty2bd_increase'] = 1
    # R['init_boundary_penalty'] = 1000  # Regularization parameter for boundary conditions
    R['init_boundary_penalty'] = 100  # Regularization parameter for boundary conditions

    # 网络的频率范围设置
    R['freqs'] = np.concatenate(([1], np.arange(1, 100 - 1)), axis=0)

    # &&&&&&&&&&&&&&&&&&&&&& 隐藏层的层数和每层神经元数目 &&&&&&&&&&&&&&&&&&&&&&&&&&&&
    # R['hidden_layers'] = (100, 10, 8, 6, 4)  # 测试
    # R['hidden_layers'] = (100, 80, 60, 60, 40, 40, 20)
    # R['hidden_layers'] = (200, 100, 80, 50, 30)
    # R['hidden_layers'] = (300, 200, 150, 100, 100, 50, 50)
    R['hidden_layers'] = (500, 400, 400, 200, 200)                                     # 待选择的网络规模
    # R['hidden_layers'] = (500, 400, 300, 300, 200, 100)
    # R['hidden_layers'] = (500, 400, 300, 200, 200, 100)
    # R['hidden_layers'] = (500, 400, 300, 300, 200, 100, 100)
    # R['hidden_layers'] = (500, 300, 200, 200, 100, 100, 50)
    # R['hidden_layers'] = (1000, 800, 600, 400, 200)
    # R['hidden_layers'] = (1000, 500, 400, 300, 300, 200, 100, 100)
    # R['hidden_layers'] = (2000, 1500, 1000, 500, 250)

    # &&&&&&&&&&&&&&&&&&& 使用的网络模型 &&&&&&&&&&&&&&&&&&&&&&&&&&&
    # R['model'] = 'PDE_DNN'
    # R['model'] = 'PDE_DNN_BN'
    # R['model'] = 'PDE_DNN_scale'
    # R['model'] = 'PDE_DNN_adapt_scale'
    R['model'] = 'PDE_DNN_FourierBase'

    # &&&&&&&&&&&&&&&&&&& 激活函数的选择 &&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    # R['activate_func'] = 'relu'
    # R['activate_func'] = 'tanh'
    # R['activate_func'] = 'sintanh'
    # R['activate_func']' = leaky_relu'
    # R['activate_func'] = 'srelu'
    R['activate_func'] = 's2relu'
    # R['activate_func'] = 's3relu'
    # R['activate_func'] = 'csrelu'
    # R['activate_func'] = 'gauss'
    # R['activate_func'] = 'singauss'
    # R['activate_func'] = 'metican'
    # R['activate_func'] = 'modify_mexican'
    # R['activate_func'] = 'leaklysrelu'
    # R['activate_func'] = 'slrelu'
    # R['activate_func'] = 'elu'
    # R['activate_func'] = 'selu'
    # R['activate_func'] = 'phi'
    # R['activate_func'] = 'sin_modify_mexican'

    solve_laplace(R)
