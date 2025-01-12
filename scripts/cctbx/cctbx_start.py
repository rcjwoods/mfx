# -*- coding: utf-8 -*-
"""
cctbx_start
"""
import argparse
import sys
import logging
import os
import subprocess

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

def check_settings(exp, cctbx_dir):
    logging.info("Checking xfel gui phil File")
    settings = f'''\
facility {{
  name = *lcls standalone
  lcls {{
    experiment = "{exp}"
    web {{
      location = "S3DF"
    }}
  }}
}}
output_folder = "/sdf/data/lcls/ds/mfx/{exp}/results/common/results"
mp {{
  method = local lsf sge pbs *slurm shifter htcondor custom
  nnodes_index = 2
  nnodes_scale = 1
  nnodes_merge = 1
  nproc_per_node = 120
  queue = "milano"
  extra_options = " --account=lcls:{exp} --reservation=lcls:onshift"
  env_script = "/sdf/group/lcls/ds/tools/cctbx/build/conda_setpaths.sh"
  phenix_script = "/sdf/group/lcls/ds/tools/cctbx/phenix/phenix-1.20.1-4487/phenix_env.sh"
}}
experiment_tag = "common"
db {{
  host = "172.24.5.182"
  name = "{exp}"
  user = "{exp}"
}}\
'''

    phil_file = f"{cctbx_dir}/settings.phil"
    if os.path.isfile(phil_file):
        cctbx_settings = open(phil_file, "r", encoding="UTF-8")
        setting_lines = cctbx_settings.readlines()
        change = False
        if setting_lines[3] != f'    experiment = "{exp}"\n':
            logging.warning(f"Changing experiment to current: {exp}")
            change = True
    else:
        logging.warning(f"settings.phil file doesn't exist. Writing new one for {exp}")
        change = True

    if change:
        cctbx_settings = open(
            phil_file, "w", encoding="UTF-8")
        cctbx_settings.writelines(settings)
        cctbx_settings.close


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="startup script for cctbx on iana."
    )
    parser.add_argument(
        "--username",
        "-u",
        dest="username",
        default=None,
        help="Enter -u to specify username",
    )
    parser.add_argument(
        "--experiment",
        "-e",
        dest="experiment",
        default=None,
        help="Enter -e to specify experiment number",
    )

    return parser.parse_args(args)


def main(args):
    """
    Main entry point allowing external calls
    Entry point for console_scripts
    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    user = args.username
    exp = args.experiment

    cctbx_dir = f"/sdf/home/{user[0]}/{user}/.cctbx.xfel"
    if not os.path.exists(cctbx_dir):
        os.makedirs(cctbx_dir)

    check_settings(exp, cctbx_dir)

    logging.info("Starting up cctbx")
    proc = [
        f"ssh -YAC psana "
        f"/sdf/home/d/djr/scripts/cctbx_step2.sh"
        ]
    
    logging.info(proc)
    
    subprocess.Popen(
        proc, shell=True, 
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def run():
    """Entry point for console_scripts"""
    main(sys.argv[1:])


if __name__ == "__main__":
    run()