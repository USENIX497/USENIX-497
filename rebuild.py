#coding:utf-8

import os
import sys
import time 
import shutil
sys.path.append(sys.path[0]+"\\An_attack_instance")

sys.path.append(sys.path[0]+"\\An_attack_instance\\target")
sys.path.reverse()
from RF_demo import test_apk

def modifyAPP(feature_path, depress_path):
    all_funcs = []
    function_calls = []
    caller_dict = {}
    add_calls = []

    function_call_path = sys.path[1]+'\\'+feature_path + '/func_calls.txt'
    all_funcs_path = sys.path[1]+'\\'+ feature_path + '/all_functions.txt'

    with_d_min_state_path =sys.path[1]+'\\'+ 'pertubation.txt'
    print(all_funcs_path)
    for line in open(all_funcs_path, 'r', encoding='utf-8'):
        all_funcs.append(line.strip())

    for line in open(function_call_path, 'r', encoding='utf-8'):
        function_calls.append(line.strip())

    with_d_min_state = []
    for line in open(with_d_min_state_path, 'r', encoding='utf-8'):
        caller = line.strip().split(' ')[0]
        callee = line.strip().split(' ')[1]
        caller_dict[all_funcs[int(caller)]] = []

        add_calls.append([all_funcs[int(caller)], all_funcs[int(callee)]])

    for add_call in add_calls:
        caller_dict[add_call[0]].append(add_call[1])


    for caller in caller_dict.keys():
        print(caller)
        className = caller.split(';->')[0][1:]
        methodName = caller.split(';->')[1][:]
        temp = methodName+'''
    .locals'''
        smaliFile = depress_path + '/smali/' + className + '.smali'
        if not os.path.exists(smaliFile):
            continue
        try:
            with open(smaliFile, "r", encoding='utf-8') as f:  
                data = f.read()  
                num1 = 0
                localsNum = int(data[data.index(temp)+len(temp)+1:data.index(temp)+len(temp)+3].strip())
                if localsNum < 2:
                    replaceItem = temp + ' ' + str(2) + ' #attack'
                    num1 = 2
                else:
                    replaceItem = temp + ' ' + str(localsNum) + ' #attack'
                    num1 = localsNum
                orgItem = temp + ' ' + str(num1) + ' #attack'
                if orgItem in data:
                    continue
                temp1 = '''
    :try_start_100
    const/4 v0, 0x1
    new-array v1, v0, [I
    aget v0, v1, v0'''
                temp2 = '''
    :try_end_100
    .catch Ljava/lang/Exception; {:try_start_100 .. :try_end_100} :catch_100
    :catch_100
    '''
                for callee in caller_dict[caller]:
                    callee = callee.split('(')[0]
                    callee = callee.replace('<init>', 'a')
                    temp1 = temp1 + '''
    invoke-static {}, %s()V'''%callee
        
                
                replaceItem = replaceItem + temp1 + temp2
                # print(replaceItem)
                data = data.replace(temp + ' ' + str(localsNum), replaceItem)
            with open(smaliFile, "w", encoding='utf-8') as f:
                f.write(data)
            # input()
        except Exception as e:
            print(e)



if __name__ == '__main__':

    apk_name = 'org_apk'
    apk_path = 'An_attack_instance/'+apk_name
    depress_path = 'depress/'+apk_name
    os.system(sys.path[-1]+'\\tools\\apktool.bat d %s -o %s -f'%(apk_path, depress_path))
    feature_path = 'feature'
    modifyAPP(feature_path, depress_path)
    # # rebuild
    os.system(sys.path[-1]+'\\tools\\apktool.bat b %s -f'%(depress_path))

    apk_path = 'An_attack_instance/'+'org_apk'
    modified_apk = 'An_attack_instance/'+'modified_apk'
    # test
    test_apk(apk_path)
    test_apk(modified_apk)
    # sign

