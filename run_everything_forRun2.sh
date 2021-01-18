datacardFolder=$1
#python prepareRun2Combine.py -o $datacardFolder
python prepareRun2Combine.py -o $datacardFolder -p16 datacards_201215_2016v3 -p17 datacards_201215_2017v3_prepsymm -p18 datacards_201215_2018v3_prepsymm
python run_all_limits.py $datacardFolder
python plotLimitsPerCategory.py -lumi 137.2  -limitfolder $datacardFolder #For 161718  b2j3-b4j4
#python plotLimitsPerCategory.py -lumi 137.2 -printlimits True -limitfolder $datacardFolder #For 161718, 1718, 1617
python printLimitLatexTable.py $datacardFolder #For 161718 b2j3-b4j4
#python printLimitLatexTable.py $datacardFolder False #For 161718, 1718, 1617
python run_all_closureChecks.py $datacardFolder
python run_all_impacts.py $datacardFolder
python run_all_gatherFailedFits.py $datacardFolder
python run_all_postfits.py $datacardFolder 1718
python printPostfitLatexTable.py $datacardFolder 1718
