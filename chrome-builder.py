import argparse
import http.client
import json
import os
import platform
import re
import shutil
import ssl
import stat
import subprocess
import sys
import time

if platform.system() == 'Windows':
	ONLINE = True
	USB_ROOT = 'I:\\chrome'
	BUILD_ROOT = 'F:\\docker-home'
	SAVE_ROOT = 'F:\\docker-home\\chrome'

elif platform.system() == 'Darwin':
	ONLINE = True
	USB_ROOT = '/Volumes/cactus/chrome'
	BUILD_ROOT = '/Volumes/case-sensitive/chrome'
	SAVE_ROOT = '/Users/andrew/Downloads/chrome'

elif platform.system() == 'Linux':
	ONLINE = False
	USB_ROOT = '/media/andrew/cactus/chrome'
	BUILD_ROOT = os.path.join(os.environ['HOME'], 'chrome')
	SAVE_ROOT = os.path.join(os.environ['HOME'], 'apks', 'chromium')

else:
	print('Unsupported platform', file=sys.stderr)
	exit()

SOURCE_FILES = ['chromium.tgz', 'depot_tools.tgz', 'docker.tar']
IDB_FILES = ['libmonochrome32.so.i64', 'libmonochrome64.so.i64']

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

def shell(command, capture_output=False):
	print(f'> {command}')
	return subprocess.run(command.split(), check=True, capture_output=capture_output)

def has_files(path, filenames):
	for filename in filenames:
		if not os.path.exists(os.path.join(path, filename)):
			return False
	return True

def copy_dir(from_dir, to_dir):
	if not os.path.exists(to_dir):
		os.makedirs(to_dir, exist_ok=True)

	for filename in os.listdir(from_dir):
		if filename.endswith('stamp'):
			continue
		from_path = os.path.join(from_dir, filename)
		to_path = os.path.join(to_dir, filename)
		if os.path.exists(to_path):
			continue
		if os.path.isfile(from_path):
			shutil.copy(from_path, to_path)
		else:
			shutil.copytree(from_path, to_path)

def is_version(str):
	return re.match(r'\d+\.\d+\.\d+\.\d+', str)

def version_key(s):
	result = []
	for part in s.split('.'):
		result.append(int(part))
	return result

def fetch_versions(channel, include_old=False):
	url_host = 'versionhistory.googleapis.com'
	url_path = f'/v1/chrome/platforms/android/channels/{channel}/versions/all/releases'
	if not include_old:
		url_path = url_path + '?filter=endtime=none'

	conn = http.client.HTTPSConnection(url_host, context=ssl._create_unverified_context())
	conn.request('GET', url_path)
	r = conn.getresponse()

	if r.status != 200:
		raise Exception(f'Version history api returned status code {r.status}')

	response = json.loads(r.read())
	if 'releases' not in response or len(response['releases']) < 1:
		raise Exception(f'Version history response error: "releases" not found')

	versions = set()
	for release in response['releases']:
		if 'version' not in release:
			raise Exception(f'Version history response error: "version" not found')
		versions.add(release['version'])

	return sorted(versions, key=version_key)

def update_version_history(ignore_errors=False):
	stable_versions = fetch_versions('stable', include_old=True)
	with open(os.path.join(USB_ROOT, f'versions.json'), 'w') as f:
		json.dump(stable_versions, f)

def load_version_history():
	with open(os.path.join(USB_ROOT, f'versions.json')) as f:
		return json.load(f)

def has_version_history():
	return os.path.isfile(os.path.join(USB_ROOT, f'versions.json'))

def find_new_stable_versions():
	version_history = set(load_version_history())
	saved_versions = set([v for v in os.listdir(SAVE_ROOT) if is_version(v)])
	stable_versions = saved_versions.intersection(version_history)

	saved_majors = set()
	for version in stable_versions:
		saved_majors.add(version_key(version)[0])

	versions_reversed = sorted(version_history, key=version_key, reverse=True)
	if len(saved_majors) == 0:
		return [versions_reversed[0]]

	latest_saved_major = sorted(saved_majors)[-1]

	new_versions = []
	new_majors = set()
	for version in versions_reversed:
		major = version_key(version)[0]
		if major > latest_saved_major and major not in new_majors:
			new_versions.append(version)
			new_majors.add(major)

	return new_versions

def collect_versions(default_dir, version=None):
	versions = []
	if version is None:
		versions.extend([v for v in os.listdir(default_dir) if is_version(v)])
	else:
		versions.append(version)
	return sorted(versions, key=version_key)

def copy_online_source_to_usb(version=None):
	if not os.path.exists(USB_ROOT):
		return

	for version in collect_versions(SAVE_ROOT, version):
		save_dir = os.path.join(SAVE_ROOT, version)
		usb_dir = os.path.join(USB_ROOT, version)

		if has_files(save_dir, IDB_FILES):
			continue

		if has_files(usb_dir, IDB_FILES):
			continue

		if has_files(usb_dir, SOURCE_FILES):
			continue

		print(f'Copying {version} source to USB')
		copy_dir(save_dir, usb_dir)

def copy_usb_source_to_offline(version=None):
	if not os.path.exists(USB_ROOT):
		return

	for version in collect_versions(USB_ROOT, version):
		usb_dir = os.path.join(USB_ROOT, version)
		build_dir = os.path.join(BUILD_ROOT, version)
		save_dir = os.path.join(SAVE_ROOT, version)

		if has_files(usb_dir, IDB_FILES):
			continue

		if has_files(save_dir, IDB_FILES):
			continue

		if has_files(build_dir, SOURCE_FILES):
			continue

		print(f'Copying {version} source from USB')
		copy_dir(usb_dir, build_dir)

def copy_offline_apks_to_usb(version=None):
	if not os.path.exists(USB_ROOT):
		return

	for version in collect_versions(SAVE_ROOT, version):
		save_dir = os.path.join(SAVE_ROOT, version)
		usb_dir = os.path.join(USB_ROOT, version)

		if not has_files(save_dir, IDB_FILES):
			continue

		if not has_files(usb_dir, SOURCE_FILES):
			continue

		if has_files(usb_dir, IDB_FILES):
			continue

		print(f'Copying {version} apks to USB')
		copy_dir(save_dir, usb_dir)

def copy_usb_apks_to_online(version=None):
	if not os.path.exists(USB_ROOT):
		return

	for version in collect_versions(USB_ROOT, version):
		usb_dir = os.path.join(USB_ROOT, version)
		save_dir = os.path.join(SAVE_ROOT, version)

		if not has_files(usb_dir, IDB_FILES):
			continue

		if has_files(save_dir, IDB_FILES):
			continue

		print(f'Copying {version} apks from USB')
		copy_dir(usb_dir, save_dir)

def download(version):
	if version == 'stable':
		stable_versions = load_version_history()
		version = stable_versions[-1]
		print(f'Downloading version {version}')

	elif version in ['beta', 'dev', 'canary']:
		versions = fetch_versions(version, include_old=False)
		version = versions[-1]
		print(f'Downloading version {version}')

	save_dir = os.path.join(SAVE_ROOT, version)

	if has_files(save_dir, SOURCE_FILES):
		print(f'{version} already downloaded')
		return

	name = f'chrome_{version}'
	if name in shell('docker container ls -a', capture_output=True).stdout.decode():
		raise Exception(f'Container {name} already exists')

	# Windows directories are case insensitive by default. This causes
	# 'gclient sync' to fail starting with commit 5dd6f3c (114.0.5683.0). See
	# https://stackoverflow.com/questions/15599592/compiling-linux-kernel-error-xt-connmark-h
	# You can query and change case sensitivity (from an admin shell) with:
	#   fsutil.exe file queryCaseSensitiveInfo <path>
	#   fsutil.exe file setCaseSensitiveInfo <path> enable
	# Newly created child directories will inherit the case sensitivity
	if platform.system() == 'Windows':
		if 'disabled' in shell(f'fsutil.exe file queryCaseSensitiveInfo {BUILD_ROOT}', capture_output=True).stdout.decode():
			raise Exception(f'{BUILD_ROOT} must be case sensitive')

	# Mac directories are also case insensitive by default
	if platform.system() == 'Darwin':
		temp_filename = 'CASE_SENSITIVITY_CHECK'
		with open(os.path.join(BUILD_ROOT, temp_filename), 'w'):
			if os.path.exists(os.path.join(BUILD_ROOT, temp_filename.lower())):
				raise Exception(f'{BUILD_ROOT} must be case sensitive')
		os.remove(os.path.join(BUILD_ROOT, temp_filename))

	script_src = os.path.join(SCRIPT_DIR, 'download.sh')
	script_dst = os.path.join(BUILD_ROOT, 'download.sh')
	shutil.copy(script_src, script_dst)

	shell('docker image pull ubuntu:20.04')
	shell(f'docker container run --name {name} --env VERSION={version} --mount type=bind,source={BUILD_ROOT},target=/home -e HOME=/home ubuntu:20.04 /home/download.sh')
	shell(f'docker container commit {name} {name}')
	shell(f'docker image save -o {save_dir}\\docker.tar {name}')
	shell(f'docker container rm {name}')
	shell(f'docker image rm {name}')

	os.remove(script_dst)

	return version

def build(version):
	save_dir = os.path.join(SAVE_ROOT, version)
	build_dir = os.path.join(BUILD_ROOT, version)

	if has_files(save_dir, IDB_FILES):
		print(f'{version} already built')
		return

	name = f'chrome_{version}'
	user = f'{os.getuid()}:{os.getgid()}'

	if not has_files(build_dir, SOURCE_FILES):
		raise Exception(f'ERROR: No source found for {version}')

	script_src = os.path.join(SCRIPT_DIR, 'build.sh')
	script_dst = os.path.join(build_dir, 'build.sh')
	shutil.copy(script_src, script_dst)

	shell(f'docker load -i {build_dir}/docker.tar')
	shell(f'docker container run --rm --user {user} --mount type=bind,source={build_dir},target=/home -e HOME=/home {name} /home/build.sh')
	shell(f'docker image rm {name}')

	copy_dir(os.path.join(build_dir, 'save'), save_dir)
	shutil.rmtree(os.path.join(build_dir, 'save'))

	for filename in SOURCE_FILES:
		os.remove(os.path.join(build_dir, filename))

	if os.path.exists(os.path.join(build_dir, 'vpython_root.tgz')):
		os.remove(os.path.join(build_dir, 'vpython_root.tgz'))

	os.remove(script_dst)

	shell(f'idat -A -L{SCRIPT_DIR}/ida64.log -S{SCRIPT_DIR}/create_idb.idc {save_dir}/libmonochrome64.so')
	shell(f'idat -A -L{SCRIPT_DIR}/ida32.log -S{SCRIPT_DIR}/create_idb.idc {save_dir}/libmonochrome32.so')

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--sync', action='store_true', help='Sync files to and from USB')
	if ONLINE:
		parser.add_argument('--download', metavar='VERSION', help='Download source for a version of Chromium')
	else:
		parser.add_argument('--build', metavar='VERSION', help='Build a version of Chromium')
	args = parser.parse_args()

	if ONLINE and args.download:
		update_version_history()
		version = download(args.download)
		if version:
			copy_online_source_to_usb(version)
		exit()

	if not ONLINE and args.build:
		copy_usb_source_to_offline(args.build)
		build(args.build)
		copy_offline_apks_to_usb(args.build)
		exit()

	if args.sync:
		if not os.path.exists(USB_ROOT):
			print('USB directory not found', file=sys.stderr)
			exit()

		if ONLINE:
			copy_usb_apks_to_online()
			copy_online_source_to_usb()

		if not ONLINE:
			copy_offline_apks_to_usb()
			copy_usb_source_to_offline()

		exit()
