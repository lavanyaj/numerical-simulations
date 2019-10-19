#!/bin/bash

source parallel.sh
ok="y"
function setup_for_robustness_approx {
    EXPERIMENT="robustness-approx"
    KW=$1
    START=$2
    END=$3
    MAX_CPUS=$4
    declare -a ROUTING_MATRIX_PROPS=(
	#"NUM_LINKS=1000; NUM_FLOWS=1000; PATH_LENGTH=5;"
	#"NUM_LINKS=1000; NUM_FLOWS=1000; PATH_LENGTH=10;"
	#"NUM_LINKS=100; NUM_FLOWS=10000; PATH_LENGTH=5;"
	"NUM_LINKS=100; NUM_FLOWS=1000; PATH_LENGTH=5;"
	"NUM_LINKS=100; NUM_FLOWS=100; PATH_LENGTH=5;"
	#"NUM_LINKS=100; NUM_FLOWS=10000; PATH_LENGTH=10;"
	"NUM_LINKS=100; NUM_FLOWS=1000; PATH_LENGTH=10;"
	"NUM_LINKS=100; NUM_FLOWS=100; PATH_LENGTH=10;"
    )
    declare -a SEED_PATH_LINKSS=( $(seq ${START} ${END} ) ) # 20

    declare -a DIVISION_SETTINGS=(
    #"DIVISION_N=0; DIVISION_L=0; DIVISION_M=0; DIVISION_ERR=0.0;"
    "DIVISION_N=32; DIVISION_L=14; DIVISION_M=12; DIVISION_ERR=0.0;"
    "DIVISION_N=32; DIVISION_L=12; DIVISION_M=10; DIVISION_ERR=0.01;"
    "DIVISION_N=32; DIVISION_L=10; DIVISION_M=8; DIVISION_ERR=0.02;"
    )

    SPERC_TIMEOUT="1.0"
    declare -a ALGS=( "sperc_robust" )

    NUM_RUNS=0
    for SEED_PATH_LINKS in "${SEED_PATH_LINKSS[@]}" ; do
	for ROUTING_MATRIX_PROP in "${ROUTING_MATRIX_PROPS[@]}" ; do
	    for DIVISION_SETTING in "${DIVISION_SETTINGS[@]}" ; do
		for ALG in "${ALGS[@]}" ; do
		    NUM_RUNS=$((NUM_RUNS+1))
		    eval ${ROUTING_MATRIX_PROP};
		    eval ${DIVISION_SETTING};
		    # We set DIVISION_* according to array, all other settings are the same as in sparse_ct experiments.
		    CONFIG="NUM_LINKS=${NUM_LINKS}; NUM_FLOWS=${NUM_FLOWS}; LONGEST_PATH=${PATH_LENGTH}; SHORTEST_PATH=${PATH_LENGTH}; SEED_PATH_LINKS=${SEED_PATH_LINKS}; SEED_LINK_DELAY=100; SEED_START_TIMEOUT=1; ALG=${ALG}; NUM_SIMS=1; CHANGE_FLOWS=1; SEED_PATH_LEN=1; SEED_LINK_CAP=1; MIN_CAPACITY=10; MAX_CAPACITY=10; SEED_PATH_LEN=1; SEED_STOP_FLOWS=1; SEED_DROP=1; SEED_START_TIMEOUT=1; RUN_INDEX=${NUM_RUNS}; SUFFIX=${KW}; SPERC_TIMEOUT=${SPERC_TIMEOUT}; DIVISION_N=${DIVISION_N}; DIVISION_L=${DIVISION_L}; DIVISION_M=${DIVISION_M}; DIVISION_ERR=${DIVISION_ERR}; DROP_PROBABILITY=0; RTO=0; MAX_NUM_RTTS=200; WARN_IF_INFEASIBLE=\\\"msg_min_alloc source_latest_min_alloc\\\"; LOOKUP_HINT_MAXFLOWS=${NUM_FLOWS}; SPERC_PRECISION=1e-7; "
		    job_list+=(" ./run_experiment.sh run_experiment_using_config ${EXPERIMENT} \"${CONFIG}\"  ${KW} &")
		    echo "job $i: ${job_list[i]}"
		    err_str_list+=("couldn't run ${EXPERIMENT} for ${ALG} with division using lookup table (N=${DIVISION_N}, l=${DIVISION_L}, m=${DIVISION_M} (error ${DIVISION_ERR})")
		    i=$((i+1));
		done
	    done
	done
    done
    #read -p "Okay to run? (y/n)" ok
    if [ "${ok}" == "y" ]; then
	run_in_parallel job_list err_str_list ${MAX_CPUS}
    fi

}

function setup_for_robustness_drop {
    EXPERIMENT="robustness-drop"
    KW=$1
    START=$2
    END=$3
    MAX_CPUS=$4

    declare -a ROUTING_MATRIX_PROPS=(
	"NUM_LINKS=1000; NUM_FLOWS=1000; PATH_LENGTH=5;"
	"NUM_LINKS=1000; NUM_FLOWS=1000; PATH_LENGTH=10;"
	"NUM_LINKS=100; NUM_FLOWS=10000; PATH_LENGTH=5;"
	"NUM_LINKS=100; NUM_FLOWS=1000; PATH_LENGTH=5;"
	"NUM_LINKS=100; NUM_FLOWS=100; PATH_LENGTH=5;"
	"NUM_LINKS=100; NUM_FLOWS=10000; PATH_LENGTH=10;"
	"NUM_LINKS=100; NUM_FLOWS=1000; PATH_LENGTH=10;"
	"NUM_LINKS=100; NUM_FLOWS=100; PATH_LENGTH=10;"
    )
    declare -a SEED_PATH_LINKSS=( $(seq ${START} ${END} ) ) # 20

    declare -a DROP_PROBABILITIES=( "0.01" "0.001" )


    SPERC_TIMEOUT="1.0"
    declare -a ALGS=( "sperc_robust" )

    NUM_RUNS=0
    for SEED_PATH_LINKS in "${SEED_PATH_LINKSS[@]}" ; do
	for ROUTING_MATRIX_PROP in "${ROUTING_MATRIX_PROPS[@]}" ; do
	    for DROP_PROBABILITY in "${DROP_PROBABILITIES[@]}" ; do
		for ALG in "${ALGS[@]}" ; do
		    NUM_RUNS=$((NUM_RUNS+1))
		    eval ${ROUTING_MATRIX_PROP};
		    # We set RTO to 2, DROP_PROBABILITIES according to array, all other settings are the same as in sparse_ct experiments.
		    CONFIG="NUM_LINKS=${NUM_LINKS}; NUM_FLOWS=${NUM_FLOWS}; LONGEST_PATH=${PATH_LENGTH}; SHORTEST_PATH=${PATH_LENGTH}; SEED_PATH_LINKS=${SEED_PATH_LINKS}; SEED_LINK_DELAY=100; SEED_START_TIMEOUT=1; ALG=${ALG}; NUM_SIMS=1; CHANGE_FLOWS=1; SEED_PATH_LEN=1; SEED_LINK_CAP=1; MIN_CAPACITY=10; MAX_CAPACITY=10; SEED_PATH_LEN=1; SEED_STOP_FLOWS=1; SEED_DROP=1; SEED_START_TIMEOUT=1; RUN_INDEX=${NUM_RUNS}; SUFFIX=${KW}; SPERC_TIMEOUT=${SPERC_TIMEOUT}; DIVISION_N=0; DIVISION_L=0; DIVISION_M=0; DIVISION_ERR=\"0.0\"; DROP_PROBABILITY=${DROP_PROBABILITY}; RTO=2; MAX_NUM_RTTS=200; WARN_IF_INFEASIBLE=\\\"msg_min_alloc source_latest_min_alloc\\\"; LOOKUP_HINT_MAXFLOWS=${NUM_FLOWS}; SPERC_PRECISION=1e-7; THRESHOLDS=\\\"0.01 0.1 0.2 0.3 0.5\\\";"
		    job_list+=(" ./run_experiment.sh run_experiment_using_config ${EXPERIMENT} \"${CONFIG}\"  ${KW} &")
		    echo "job $i: ${job_list[i]}"
		    err_str_list+=("couldn't run ${EXPERIMENT} for ${ALG} with drop prob. ${DROP_PROBABILITY}")
		    i=$((i+1));
		done
	    done
	done
    done
    #read -p "Okay to run? (y/n)" ok
    if [ "${ok}" == "y" ]; then
	run_in_parallel job_list err_str_list ${MAX_CPUS}
    fi

}

function setup_for_basic_ct {
    EXPERIMENT=$1
    START=$2
    END=$3
    MAX_CPUS=$4;
    KW=$5;
    shift 5;
    ROUTING_MATRIX_PROPS=("$@")

    echo "function setup_for_basic_ct got arguments EXPERIMENT ${EXPERIMENT} START ${START} END ${END}  MAX_CPUS ${MAX_CPUS} KW ${KW} and an array ROUTING_MATRIX_PROPS"

    declare -a SEED_PATH_LINKSS=( $(seq ${START} ${END} ) )

    SPERC_TIMEOUT="1.0"
    declare -a ALGS=( "sperc_basic" "perc" "naive" "sperc_ignore" )

    NUM_RUNS=0
    for SEED_PATH_LINKS in "${SEED_PATH_LINKSS[@]}" ; do
	echo "SEED_PATH_LINKS is ${SEED_PATH_LINKS}"
	for ROUTING_MATRIX_PROP in "${ROUTING_MATRIX_PROPS[@]}" ; do
	    for ALG in "${ALGS[@]}" ; do
		NUM_RUNS=$((NUM_RUNS+1))
		echo "routing matrix prop is ${ROUTING_MATRIX_PROP}"
		eval ${ROUTING_MATRIX_PROP};
		CONFIG="NUM_LINKS=${NUM_LINKS}; NUM_FLOWS=${NUM_FLOWS}; LONGEST_PATH=${PATH_LENGTH}; SHORTEST_PATH=${PATH_LENGTH}; SEED_PATH_LINKS=${SEED_PATH_LINKS}; SEED_LINK_DELAY=100; SEED_START_TIMEOUT=1; ALG=${ALG}; NUM_SIMS=1; CHANGE_FLOWS=1; SEED_PATH_LEN=1; SEED_LINK_CAP=1; MIN_CAPACITY=10; MAX_CAPACITY=10; SEED_PATH_LEN=1; SEED_STOP_FLOWS=1; SEED_DROP=1; SEED_START_TIMEOUT=1; RUN_INDEX=${NUM_RUNS}; SUFFIX=${KW}; SPERC_TIMEOUT=${SPERC_TIMEOUT}; DIVISION_N=0; DIVISION_L=0; DIVISION_M=0; DIVISION_ERR=\"0.0\"; DROP_PROBABILITY=0; RTO=0; MAX_NUM_RTTS=200; WARN_IF_INFEASIBLE=\\\"msg_min_alloc source_latest_min_alloc\\\"; LOOKUP_HINT_MAXFLOWS=${NUM_FLOWS}; SPERC_PRECISION=1e-7; "
		    job_list+=(" ./run_experiment.sh run_experiment_using_config ${EXPERIMENT} \"${CONFIG}\"  ${KW} &")
		    echo "job $i: ${job_list[i]}"
		    err_str_list+=("couldn't run ${EXPERIMENT} for ${ALG}")
		    i=$((i+1));
	    done
	done
    done
    #read -p "Okay to run? (y/n)" ok
    if [ "${ok}" == "y" ]; then
	run_in_parallel job_list err_str_list ${MAX_CPUS}
    fi

}

function setup_for_sparse_ct {
    KW=$1
    START=$2
    END=$3
    MAX_CPUS=$4

    EXPERIMENT="sparse-ct"
    declare -a ROUTING_MATRIX_PROPS=(  
	"NUM_LINKS=1000; NUM_FLOWS=1000; PATH_LENGTH=5;"
	"NUM_LINKS=1000; NUM_FLOWS=1000; PATH_LENGTH=10;"
     	"NUM_LINKS=100; NUM_FLOWS=10000; PATH_LENGTH=5;"
     	"NUM_LINKS=100; NUM_FLOWS=1000; PATH_LENGTH=5;"
     	"NUM_LINKS=100; NUM_FLOWS=100; PATH_LENGTH=5;"
     	"NUM_LINKS=100; NUM_FLOWS=10000; PATH_LENGTH=10;"
     	"NUM_LINKS=100; NUM_FLOWS=1000; PATH_LENGTH=10;"
     	"NUM_LINKS=100; NUM_FLOWS=100; PATH_LENGTH=10;"
    )
    # can only pass one array to a bash function, and it must be the last argument
    setup_for_basic_ct $EXPERIMENT ${START} ${END} ${MAX_CPUS} ${KW} "${ROUTING_MATRIX_PROPS[@]}"
}

function setup_for_dense_ct {
    KW=$1
    START=$2
    END=$3
    MAX_CPUS=$4

    echo "function setup_for_dense_ct got arguments KW ${KW} START ${START}, END ${END}, MAX_CPUS ${MAX_CPUS}"
    EXPERIMENT="dense-ct"
    declare -a ROUTING_MATRIX_PROPS=(  
	"NUM_LINKS=100; NUM_FLOWS=100; PATH_LENGTH=80;"
    )
    # can only pass one array to a bash function, and it must be the last argument
    #setup_for_basic_ct $EXPERIMENT ${START} ${END} ${MAX_CPUS} ${KW} ROUTING_MATRIX_PROPS
    setup_for_basic_ct $EXPERIMENT ${START} ${END} ${MAX_CPUS} ${KW} "${ROUTING_MATRIX_PROPS[@]}"

}


function set_env_vars {
    EXPERIMENT=$1
    declare -a cmds=(
	"export HOME_DIR=`echo ~`" 
	"export NUMERICAL_DIR=\${HOME_DIR}/numerical"
	"export NUMERICAL_RUN_LOG=\${NUMERICAL_DIR}/drive-out"
	"export NUMERICAL_RUN_FILES=\${NUMERICAL_DIR}/run-files"
	"if [ ! -e \${NUMERICAL_RUN_LOG} ];  then mkdir \${NUMERICAL_RUN_LOG}; fi;"
	"if [ ! -e \${NUMERICAL_RUN_FILES} ];  then mkdir \${NUMERICAL_RUN_FILES}; fi;"
	"if [ ! -e \${NUMERICAL_RUN_FILES}/\${EXPERIMENT} ];  then mkdir \${NUMERICAL_RUN_FILES}/\${EXPERIMENT}; fi;"
	"if [ ! -e \${NUMERICAL_RUN_FILES}/\${EXPERIMENT}/results ];  then mkdir \${NUMERICAL_RUN_FILES}/\${EXPERIMENT}/results; fi;"
    )

    #declare -s EXPERIMENTS=( "sparse-ct", "dense-ct", "robust-div", "robust-drop", "sperci-prec" )
    run_in_sequence cmds
    echo ${HOME_DIR}
    echo ${NUMERICAL_DIR}
    echo ${NUMERICAL_RUN_LOG}
    echo ${NUMERICAL_RUN_FILES}
    ls ${NUMERICAL_RUN_FILES}
    ls ${NUMERICAL_RUN_FILES}/${EXPERIMENT}
}


function run_experiment_using_config {
    EXPERIMENT=$1;
    CONFIG=$2;
    KW=$3;  # just a keyword to distinguish runs

    echo "EXPERIMENT ${EXPERIMENT}"
    echo "KW ${KW}"

    echo "CONFIG $CONFIG"
    eval $CONFIG

    echo "ALG ${ALG}"
    echo "CONFIG ${CONFIG}"

    START_DIR=`pwd`;

    # set env vars
    set_env_vars ${EXPERIMENT}

    cmds=()
    if ( [ "${EXPERIMENT}" == "sparse-ct" ] || [ "${EXPERIMENT}" == "dense-ct" ] ); then
    	# Vary NUM_LINKS, NUM_FLOWS, LONGEST_PATH, ALG for this experiment.
    	NAME="${EXPERIMENT}_alg=${ALG}_links=${NUM_LINKS}_flows=${NUM_FLOWS}_path=${LONGEST_PATH}_seed-path-links=${SEED_PATH_LINKS}_kw=${KW}"
    else
	if ( [ "${EXPERIMENT}" == "robustness-drop" ] ); then
	    NAME="${EXPERIMENT}_alg=${ALG}_links=${NUM_LINKS}_flows=${NUM_FLOWS}_path=${LONGEST_PATH}_seed-path-links=${SEED_PATH_LINKS}_drop-prob=${DROP_PROBABILITY}_rto=${RTO}_kw=${KW}"
	else
	    if ( [ "${EXPERIMENT}" == "robustness-approx" ] ); then
		NAME="${EXPERIMENT}_alg=${ALG}_links=${NUM_LINKS}_flows=${NUM_FLOWS}_path=${LONGEST_PATH}_seed-path-links=${SEED_PATH_LINKS}_N=${DIVISION_N}_m=${DIVISION_M}_l=${DIVISION_L}_kw=${KW}"
	    else
    		echo "EXPERIMENT ${EXPERIMENT} not implemented."
    		return -1;
	    fi
	fi
    fi;


    LINK_FILENAME="${NUMERICAL_RUN_FILES}/${EXPERIMENT}/links-${NAME}.txt";
    FLOW_FILENAME="${NUMERICAL_RUN_FILES}/${EXPERIMENT}/flows-${NAME}.txt";
    CT_FILENAME="${NUMERICAL_RUN_FILES}/${EXPERIMENT}/results/ct-${NAME}";
    RS_FILENAME_PREFIX="${NUMERICAL_RUN_FILES}/${EXPERIMENT}/rs_log-${NAME}";
    RS_FILENAME_FLOW_RATES="${RS_FILENAME_PREFIX}-flow-rates";  # check run_simulations.py
    LOG_OUT="${NUMERICAL_RUN_LOG}/log-${NAME}.out";
    LOG_ERR="${NUMERICAL_RUN_LOG}/log-${NAME}.err";

    cmds+=("echo \"Log (out) start at time: $(date).\" >> ${LOG_OUT}")
    cmds+=("echo \"Log (err) start at time: $(date).\" >> ${LOG_ERR}")


    cmds+=("echo ${CONFIG} >> ${LOG_OUT};")
    
    cmds+=("python generate_simple_links.py --num_links ${NUM_LINKS} --longest_path  ${LONGEST_PATH} --min_capacity ${MIN_CAPACITY} --max_capacity ${MAX_CAPACITY} --link_filename ${LINK_FILENAME} --timeout_in_rtts ${SPERC_TIMEOUT} --seed_link_cap ${SEED_LINK_CAP} --division_N ${DIVISION_N} --division_l ${DIVISION_L} --division_m ${DIVISION_M} --sperc_precision ${SPERC_PRECISION} --drop_probability ${DROP_PROBABILITY} --rto ${RTO} --max_num_rtts ${MAX_NUM_RTTS} 1> /dev/null 2> ${LOG_ERR};")

    cmds+=("python generate_simple_flows.py --longest_path ${LONGEST_PATH}  --shortest_path ${SHORTEST_PATH} --num_links ${NUM_LINKS} --num_flows ${NUM_FLOWS} --num_sims ${NUM_SIMS} --change_flows ${CHANGE_FLOWS} --flow_filename ${FLOW_FILENAME} --seed_stop_flows ${SEED_STOP_FLOWS} --seed_path_links ${SEED_PATH_LINKS} --seed_path_len ${SEED_PATH_LEN} 1> /dev/null 2> ${LOG_ERR};")
	
    cmds+=("python run_simulations.py --alg ${ALG} --seed_link_delay ${SEED_LINK_DELAY} --seed_drop ${SEED_DROP} --seed_start_timeout ${SEED_START_TIMEOUT} --link_filename ${LINK_FILENAME} --flow_filename ${FLOW_FILENAME} --warn_if_infeasible ${WARN_IF_INFEASIBLE} --lookup_hint_maxflows ${LOOKUP_HINT_MAXFLOWS} --log_dir_path ${RS_FILENAME_PREFIX} 1>${LOG_OUT} 2> ${LOG_ERR};")


    cmds+=("python get_convergence_times.py --thresholds ${THRESHOLDS} --input_files ${RS_FILENAME_FLOW_RATES} 1> ${CT_FILENAME} 2> ${LOG_ERR};")

    #cmds+=("rm ${LOG_OUT};")

    run_in_sequence cmds
}


if [ "$1" == "run_experiment_using_config" ] ; then
    echo "run_experiment_using_config"
    echo "EXPERIMENT $2"
    echo "CONFIG $3"
    echo "KW $4"
    run_experiment_using_config $2 "$3" $4
fi;

KW="oct19a"
START=1
END=2
MAX_CPUS=4

if [ "$1" == "sparse-ct" ] ; then
    setup_for_sparse_ct $KW ${START} ${END} ${MAX_CPUS}
fi;

if [ "$1" == "dense-ct" ] ; then
    setup_for_dense_ct $KW ${START} ${END} ${MAX_CPUS}
fi;

if [ "$1" == "robustness-drop" ] ; then
    setup_for_robustness_drop $KW ${START} ${END} ${MAX_CPUS}
fi;

if [ "$1" == "robustness-approx" ] ; then
    setup_for_robustness_approx $KW ${START} ${END} ${MAX_CPUS}
fi;
