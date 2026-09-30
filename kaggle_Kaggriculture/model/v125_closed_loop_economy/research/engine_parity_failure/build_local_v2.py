#!/usr/bin/env python3
"""使用已有缓存头文件直接编译本地派生模块；不安装依赖、不替换原库。"""
import hashlib,json,subprocess,sysconfig
from pathlib import Path

root=Path(__file__).resolve().parent/'slotfix_build_v2'
include=Path('/Users/a1-6/.cache/uv/archive-v0/kaHRm5eu7Ou4hYFP/pybind11/include')
assert (include/'pybind11/pybind11.h').is_file()
destination=root/('kagsim_slotfix'+sysconfig.get_config_var('EXT_SUFFIX'))
assert not destination.exists(),'拒绝覆盖已有派生库'
command=['clang++','-O3','-Wall','-shared','-std=c++17','-fPIC','-fvisibility=hidden','-undefined','dynamic_lookup',
         '-I'+sysconfig.get_paths()['include'],'-I'+str(include),str(root/'python/kagsim.cpp'),'-o',str(destination)]
version=subprocess.run(['clang++','--version'],capture_output=True,text=True,check=True).stdout
result=subprocess.run(command,cwd=root,capture_output=True,text=True)
(root/'compiler.stdout.log').write_text(result.stdout);(root/'compiler.stderr.log').write_text(result.stderr)
meta={'command':command,'compiler_version':version,'exit_code':result.returncode,'header_source':'已有uv缓存，未安装或下载任何依赖',
      'headers_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(include.rglob('*.h'))},
      'output_path':str(destination),'output_sha256':hashlib.sha256(destination.read_bytes()).hexdigest() if destination.exists() else None}
(root/'build_execution.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in meta.items() if k!='headers_sha256'},ensure_ascii=False,indent=2))
assert result.returncode==0
