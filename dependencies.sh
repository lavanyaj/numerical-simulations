#!/bin/bash

source /usr/bin/parallel.sh

function run_in_sequence {
    local -n __cmds_list=$1;
    for cmd in "${__cmds_list[@]}"; do
	eval $cmd
	success=$?
	if [ $success != 0 ]; then
	    echo "failed to run $cmd;"
	    exit $success
	else
	    echo $cmd
	fi;
    done;
}

function install_anaconda {
    declare -a cmds=(
	"wget https://repo.continuum.io/archive/Anaconda2-4.1.1-Linux-x86_64.sh"
	"bash Anaconda2-4.1.1-Linux-x86_64.sh -b -p ${HOME}/anaconda"	
	"jupyter"
    );
    run_in_sequence cmds
}

function install_deps {
   # build NS-2 binaries for s-PERC, RCP, and DCTCP (same binary used to run p-Fabric)
    max_cpus=3;
    job_list=()
    err_str_list=()


    job_list+=(" sudo apt-get -y install git &")
    err_str_list+=("couldn't install git")    
    echo "${job_list[0]}"

    job_list+=(" sudo apt-get -y install emacs24 &")
    err_str_list+=("couldn't install emacs24")    
    echo "${job_list[1]}"


    job_list+=(" ./dependencies.sh anaconda &")
    err_str_list+=("couldn't install anaconda for jupyter notebooks")    
    echo "${job_list[2]}"

    job_list+=(" sudo apt-get -y install python3-matplotlib &")
    err_str_list+=("couldn't install python3-matplotlib")    
    echo "${job_list[3]}"

    job_list+=(" sudo apt-get -y install python-matplotlib &")
    err_str_list+=("couldn't install python-matplotlib")    
    echo "${job_list[4]}"

    job_list+=(" sudo apt-get -y install python3-numpy &")
    err_str_list+=("couldn't install python3-numpy")    
    echo "${job_list[5]}"

    job_list+=(" sudo apt-get -y install python-numpy &")
    err_str_list+=("couldn't install python-numpy")    
    echo "${job_list[6]}"

    job_list+=(" sudo apt-get -y install python3-pandas &")
    err_str_list+=("couldn't install python3-pandas")    
    echo "${job_list[7]}"

    job_list+=(" sudo apt-get -y install python-pandas &")
    err_str_list+=("couldn't install python-pandas")    
    echo "${job_list[8]}"


    read -p "Will use up to ${max_cpus} CPUs. Okay to run? (y/n)" ok
    if [ "${ok}" == "y" ]; then
	run_in_parallel job_list err_str_list ${max_cpus}
    fi
}


if [ "$1" == "anaconda" ] ; then
    install_anaconda
else
    install_deps
fi;
