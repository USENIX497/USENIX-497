## -*- coding: utf-8 -*- 
import os 
import sys
import re
import numpy as np
from sklearn.externals import joblib
import random
import scipy.sparse as sp
seed = 123
random.seed(seed)
np.random.seed(seed + 1)
INVOKE_PATTERN = re.compile(
    '(?P<invoketype>invoke-(?:virtual|direct|static|super|interface)) (?:\{.*\}), (?P<method>L.+;->.+)(?:\n)')

CLASS_NAME_PATTERN = re.compile('\.class.*(?P<clsname>L.*)(?:;)')
METHOD_BLOCK_PATTERN = re.compile('\.method.* (?P<methodname>.*)\n.*\n((?:.|\n)*?)\.end method')
packages_list = []
for line in open('granularity/packages_mama.txt', 'r', encoding='utf-8'):
    packages_list.append(line.strip())
allpacks=[]
for i in packages_list:
    allpacks.append(i.split('.')[:])
pos_p=[[],[],[],[],[],[],[],[],[]]
for i in allpacks:
    k=len(i)
    for j in range(0,k):
        if i[j] not in pos_p[j]:
            pos_p[j].append(i[j])
packages_list.append('self-defined')
packages_list.append('obfuscated')

def PackAbs(call,pos):

    partitions=call[1:].split(';->')[0].split('/')
    package = ""
    for i in range (0,len(partitions)):
        if partitions[i] in pos[i]:
            package=package+partitions[i]+'.'
        else:
            if package=="" or package=='com.':
                package=None
            else:
                if package.endswith('.'):
                    package=package[0:-1]
            break

    if package not in packages_list and package != None:
        partitions = package.split('.')  
        for i in range (0, len(partitions)):# 4
            package = package[0:-(len(partitions[len(partitions)-i-1])+1)]
            if package in packages_list:
                return package
    if package=="" or package=='com.':
       package=None      
    return package

def get_all_funcs_and_func_calls_from_smali_folder_path(smali_folder_path):
    all_funcs = []
    func_calls = []
    smali_file_path_all = []
    smali_folder_path = smali_folder_path + '/smali'
    for root, dirs, files in os.walk(smali_folder_path):
        for file in files:
            smali_file_path_all.append(os.path.join(root, file))
    for smali_file_path in smali_file_path_all:
        with open(smali_file_path, 'r', encoding='utf-8') as f:
            s = f.read()
            class_name_match = CLASS_NAME_PATTERN.search(s)        
            class_name = class_name_match.group(
                    'clsname') if class_name_match is not None else ''
            for method_block_match in METHOD_BLOCK_PATTERN.finditer(s):
                method_name = method_block_match.group('methodname')
                for invoke_match in INVOKE_PATTERN.finditer(method_block_match.group()):
                    cur_pair = class_name + ';->' + method_name + ' ' + \
                               invoke_match.group('invoketype') + \
                               ' ' + invoke_match.group('method')
                    
                    if cur_pair.split(' ')[0] not in all_funcs:
                        all_funcs.append(cur_pair.split(' ')[0])
                    if cur_pair.split(' ')[2] not in all_funcs:
                        all_funcs.append(cur_pair.split(' ')[2])
                    cur_pair_new = '%d %s %d'%(all_funcs.index(cur_pair.split(' ')[0]), cur_pair.split(' ')[1], all_funcs.index(cur_pair.split(' ')[2]))
                    func_calls.append(cur_pair_new)
    return all_funcs, func_calls


def model_load():
    model = joblib.load('target/my_model_RF.m')
    return model

def test(clf, test_x):
 
    answer = []
    for i in range(len(test_x)):
        res = clf.predict(test_x[i].reshape(1, -1))
        answer.append(res)
    answer = np.array(answer)
    return answer
def extract_MAMA_features_from_txt(txt_folder_path):
    function_calls = []
    all_funcs = []
 
    function_call_path =  txt_folder_path + '/func_calls.txt'
    all_funcs_path = txt_folder_path + '/all_functions.txt'
    for line in open(all_funcs_path, 'r', encoding='utf-8'):
        all_funcs.append(line.strip())
    for line in open(function_call_path, 'r', encoding='utf-8'):
        function_calls.append(line.strip())
    ########  package#####################
    package_call_times = np.zeros((len(packages_list), len(packages_list)))
    for pair in function_calls:
        caller = int(pair.split(' ')[0])
        callee = int(pair.split(' ')[2])
        pair = all_funcs[caller] +' '+ pair.split(' ')[1] +' '+  all_funcs[callee] 
        caller, callee = get_package_caller_callee_from_function_pair(pair)
        package_call_times[caller][callee] += 1
    for i in range(len(packages_list)):
        sumer = sum(package_call_times[i])
        if sumer == 0:
            continue
        for j in range(len(packages_list)):
            package_call_times[i][j] = package_call_times[i][j]/sumer
    return  package_call_times

def get_package_caller_callee_from_function_pair(function_pair):

    function_pair = function_pair.split(' ')
    match=PackAbs(function_pair[0],pos_p)
        
    if match == None:
        splitted = function_pair[0][1:].split(';->')[0].split('/')
        obfcount=0
        for k in range (0,len(splitted)):
            if len(splitted[k])<3:
                obfcount+=1
        if obfcount>=len(splitted)/2:
            match='obfuscated'
        else:
            match='self-defined'
    caller = packages_list.index(match)
    match=PackAbs(function_pair[2],pos_p)
    
    if match == None:
        splitted = function_pair[2][1:].split(';->')[0].split('/')
        obfcount=0
        for k in range (0,len(splitted)):
            if len(splitted[k])<3:
                obfcount+=1
        if obfcount>=len(splitted)/2:
            match='obfuscated'
        else:
            match='self-defined'    
    callee = packages_list.index(match)

    return caller, callee
def test_apk(apk_path):
    model = model_load()
    model_pca = joblib.load('target/pca.m')
    apk_name = apk_path.split('/')[-1]
    
    # apk_path = modified_apk
    depress_path = 'Depress/'+apk_name
    os.system('apktool.bat d %s -o %s -f'%(apk_path, depress_path))
    all_funcs, func_calls = get_all_funcs_and_func_calls_from_smali_folder_path(depress_path)
    txt_path = 'features/'+apk_name
    if not os.path.exists(txt_path):
        os.makedirs(txt_path)
    with open(txt_path+'/all_functions.txt', 'w', encoding='utf-8') as f:
        for j in range(len(all_funcs)):
            f.write(all_funcs[j]+'\n')   
    with open(txt_path+'/func_calls.txt', 'w', encoding='utf-8') as f:
        for j in range(len(func_calls)):
            f.write(func_calls[j] + '\n')   

    package_call_times = extract_MAMA_features_from_txt(txt_path)
    package_call_times = sp.coo_matrix(package_call_times).todense().reshape(-1)
    y_pred = model.predict(model_pca.transform(package_call_times))
    print("the target model's prediction: ", y_pred)



if __name__ == '__main__':
    apk_name = '6D483C8633F36854AA6F86932030BD0B05124F48A5FDDCB843BA45659546069E'
    apk_path = 'org_apk/' + apk_name
    modified_apk = 'modified_apk/' + apk_name
    test(apk_path)
    test(modified_apk)

    