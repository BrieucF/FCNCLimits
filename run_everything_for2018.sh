datacardFolder=$1 
python prepareShapesAndCards.py -p histos_suitable_for_limits_191014_2018/training_0101010101/ -dataYear 2018 -l 59741 -le 1.025 -xsecfile xsec_2018_191014.yml --sysToAvoid prefire -o $datacardFolder -removeHutb4j4 False
python run_all_limits.py $datacardFolder
python plotLimitsPerCategory.py -lumi 59.7 -limitfolder $datacardFolder -removeHutb4j4 False
python printLimitLatexTable.py $datacardFolder False
#python run_all_closureChecks.py $datacardFolder
#python run_all_impacts.py $datacardFolder
#python run_all_postfits.py $datacardFolder
