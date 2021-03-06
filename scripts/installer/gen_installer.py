import configparser
import os
import re
import subprocess
import sys
import tempfile
import zipfile

import requests


def run_cmd(label, cmdline, **kwargs):
    print(label + " " + str(cmdline))
    subprocess.run(cmdline, check=True, **kwargs)


def extract_bzt_version(bzt_dist):
    matches = re.findall(r'(\d+\.[\d.]+)', bzt_dist)
    if not matches:
        raise ValueError("Can't extract version from string %r" % bzt_dist)
    version = matches[0]
    print("Building installer for bzt %s" % version)
    return version


def generate_pynsist_config(dependencies, wheel_dir, cfg_location, bzt_version):
    print("Generating pynsist config")
    cfg = configparser.ConfigParser()
    cfg['Application'] = {
        'name': 'Taurus',
        'version': bzt_version,
        'publisher': 'CA BlazeMeter',
        'entry_point': 'scripts.installer.bzt_win:main',
        'console': 'true',
        'icon': 'site/img/taurus.ico',
        'license_file': 'LICENSE',
    }

    cfg['Command bzt'] = {
        'entry_point': 'bzt.cli:main',
        'extra_preamble': 'scripts/installer/bzt_preamble.py',
    }

    cfg['Command jmx2yaml'] = {
        'entry_point': 'bzt.jmx2yaml:main',
    }

    cfg['Command soapui2yaml'] = {
        'entry_point': 'bzt.soapui2yaml:main',
    }

    cfg['Python'] = {
        'bitness': 64,
        'version': '3.6.3',
    }

    wheels_list = ["%s==%s" % (package_name, version) for package_name, version in dependencies]
    cfg['Include'] = {
        'packages': '\n'.join(['tkinter', '_tkinter']),
        'pypi_wheels': "\n".join(wheels_list),
        'extra_wheel_sources': wheel_dir,
        'files': '\n'.join([
            'README.md',
            'lib',
            'build/nsis/tmp/chrome-loader.exe',
        ])
    }

    cfg['Build'] = {
        'installer_name': "TaurusInstaller_%s_x64.exe" % bzt_version
    }

    with open(cfg_location, 'w') as fds:
        cfg.write(fds)


def run_pynsist(cfg_location):
    run_cmd("Running pynsist", ['pynsist', cfg_location])


def fetch_all_wheels(for_package, wheel_dir):
    run_cmd("Fetching wheels", [
        "pip-custom-platform", "wheel", "--wheel-dir", wheel_dir, "--platform", "win_amd64", for_package
    ])


def extract_all_dependencies(wheel_dir):
    """Extract all (package, version) pairs from a directory with wheels"""
    print("Extracting dependent package list")
    packages = []
    for filename in os.listdir(wheel_dir):
        if filename.endswith('.whl'):
            parts = filename.split('-')
            package_name, version = parts[0], parts[1]
            packages.append((package_name, version))
    return packages


def download_tkinter(archive_url, archive_filename):
    print("Downloading tkinter archive")
    archive_filename = archive_url.split('/')[-1]
    r = requests.get(archive_url, stream=True)
    with open(archive_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    print("Unpacking tkinter libs")
    with zipfile.ZipFile(archive_filename) as z:
        z.extractall()


def main():
    if len(sys.argv) < 2:
        print("Usage: %s <bzt-wheel>" % sys.argv[0])
        sys.exit(1)
    bzt_dist = sys.argv[1]
    tkinter_link = "https://github.com/mu-editor/mu_tkinter/releases/download/0.3/pynsist_tkinter_3.6_64bit.zip"
    pynsist_config = "installer-gen.cfg"
    wheel_dir = "build/wheels"
    bzt_version = extract_bzt_version(bzt_dist)
    tkinter_archive = tempfile.NamedTemporaryFile(prefix="tkinter-libs", suffix=".zip")
    download_tkinter(tkinter_link, tkinter_archive.name)
    fetch_all_wheels(bzt_dist, wheel_dir)
    dependencies = extract_all_dependencies(wheel_dir)
    generate_pynsist_config(dependencies, wheel_dir, pynsist_config, bzt_version)
    run_pynsist(pynsist_config)


if __name__ == '__main__':
    main()
