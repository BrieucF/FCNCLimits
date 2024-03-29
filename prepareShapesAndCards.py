#! /bin/env python

# Python imports
import os, sys, stat, argparse, getpass, json
from datetime import datetime
from math import sqrt
import yaml
from collections import OrderedDict
from subprocess import call

# to prevent pyroot to hijack argparse we need to go around
tmpargv = sys.argv[:] 
sys.argv = []

# ROOT imports
import ROOT
ROOT.gROOT.SetBatch()
ROOT.PyConfig.IgnoreCommandLineOptions = True
sys.argv = tmpargv

hadNegBinForProcess = {}
hadNegBinErrForProcess = {}
def setNegativeBinsToZero(h, process):
    if not process in hadNegBinForProcess:
        hadNegBinForProcess[process] = False
    for i in range(1, h.GetNbinsX() + 1):
        if h.GetBinContent(i) < 0.:
            if not hadNegBinForProcess[process]:
                print 'Remove negative bin in TH1 %s for process %s'%(h.GetTitle(), process)
            hadNegBinForProcess[process] = True
            h.SetBinContent(i, 0.)
    
def get_hist_regex(r):
    return '^%s(__.*(up|down))?$' % r

cmssw_base = os.environ['CMSSW_BASE']

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1', 'True'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0', 'False'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

parser = argparse.ArgumentParser(description='Create shape datacards ready for combine')

parser.add_argument('-p', '--path', action='store', dest='root_path', type=str, default=cmssw_base+'/src/UserCode/FCNCLimits/histos_suitable_for_limits_200101_2017/training_0101010101', help='Directory containing rootfiles with the TH1 used for limit settings')
parser.add_argument('-l', '--luminosity', action='store', type=float, dest='luminosity', default=41529, help='Integrated luminosity (default is 41529 /pb)')
parser.add_argument('-le', '--luminosityError', action='store', type=float, dest='luminosityError', default=1.023, help='Error on the integrated luminosity (default is 1.023 /pb)')
parser.add_argument('-o', '--output', action='store', dest='output', type=str, default='datacards_200101_2017', help='Output directory')
parser.add_argument('-c' , '--channel', action='store', dest='channel', type=str, default='all', help='Channel: el, mu, or all.')
parser.add_argument('-applyxsec' , action='store', dest='applyxsec', type=bool, default=True, help='Reweight MC processes by Xsec/Nevt from yml config.')
parser.add_argument('-xsecfile' , action='store', dest='xsecfile', type=str, default='xsec_2017_200101.yml', help='YAML config file path with Xsec and Nevt.')
parser.add_argument('--nosys', action='store', dest='nosys', default=False, help='Consider or not systematic uncertainties (NB : bbb uncertainty is with another flag)')
parser.add_argument('--sysToAvoid', action='store', dest='sysToAvoid', nargs='+', default=[], help='Set it to exclude some of the systematics. Name should as in rootfile without the up/dowm postfix')
# Example to call it: python prepareShapesAndCards.py --sysToAvoid pu hf
parser.add_argument('--sysForSMtt', action='store', dest='sysForSMtt', nargs='+', default=['scale', 'TuneCP5', 'TuneCUETP', 'ps', 'pdf','hdamp'], help='Systematics affecting only SM tt.')
parser.add_argument('--sysForSig', action='store', dest='sysForSig', nargs='+', default=['scale', 'ps', 'pdf'], help='Systematics affecting Signals (must be common with SMtt)')
parser.add_argument('--correlatedSys', action='store', dest='correlatedSys', nargs='+', default=['pu', 'lepton', 'scale', 'ps', 'TuneCP5', 'TuneCUETP', 'hdamp', 'pdf', 'lf', 'hf', 'cferr1', 'cferr2'], help='Systematics that are correlated accross years. NB: cross section unc are added by hand at the end of this script, go there to change correlation for them.')
parser.add_argument('-rebinning' , action='store', dest='rebinning', type=int, default=4, help='Rebin the histograms by -rebinning.')
parser.add_argument('-dataYear' , action='store', dest='dataYear', type=str, default='2017', help='Which year were the data taken? This has to be added in datacard entries in view of combination (avoid considering e.g. correlated lumi uncertainty accross years)')
parser.add_argument('-removeHutb4j4', dest='removeHutb4j4', type=str2bool, default="False", help='Remove Hut b4j4 from plots')

options = parser.parse_args()

print options.removeHutb4j4
correlatedSys = options.correlatedSys
correlatedSys.extend(['jecAbsolute', 'jecAbsolute'+options.dataYear, 'jecBBEC1', 'jecBBEC1'+options.dataYear, 'jecFlavorQCD', 'jecRelativeBal', 'jecRelativeSample'+options.dataYear])

channel_mapping = {
    "mu" : 'Ch0',
    "el" : 'Ch1',
    "all" : 'Ch2'
    }

selection_mapping = {
    'b2j3' : 'S2',
    'b2j4' : 'S6',
    'b3j3' : 'S3',
    'b3j4' : 'S7',
    'b4j4' : 'S11'
    }

#Hct_j4_h_DNN_b2_Ch2__TuneCP5up
DNN_Hct_hist_name = 'Hct'
DNN_Hut_hist_name = 'Hut'
channel = options.channel 
individual_discriminants = { # support regex (allow to avoid ambiguities if many histogram contains same patterns)
        'DNN_Hct_b2j3': get_hist_regex('{0}_h_DNN_j3b2_{1}'.format(DNN_Hct_hist_name, channel_mapping[channel])),
        'DNN_Hct_b3j3': get_hist_regex('{0}_h_DNN_j3b3_{1}'.format(DNN_Hct_hist_name, channel_mapping[channel])),

        'DNN_Hct_b2j4': get_hist_regex('{0}_h_DNN_j4b2_{1}'.format(DNN_Hct_hist_name, channel_mapping[channel])),
        'DNN_Hct_b3j4': get_hist_regex('{0}_h_DNN_j4b3_{1}'.format(DNN_Hct_hist_name, channel_mapping[channel])),
        'DNN_Hct_b4j4': get_hist_regex('{0}_h_DNN_j4b4_{1}'.format(DNN_Hct_hist_name, channel_mapping[channel])),

        'DNN_Hut_b2j3': get_hist_regex('{0}_h_DNN_j3b2_{1}'.format(DNN_Hut_hist_name, channel_mapping[channel])),
        'DNN_Hut_b3j3': get_hist_regex('{0}_h_DNN_j3b3_{1}'.format(DNN_Hut_hist_name, channel_mapping[channel])),

        'DNN_Hut_b2j4': get_hist_regex('{0}_h_DNN_j4b2_{1}'.format(DNN_Hut_hist_name, channel_mapping[channel])),
        'DNN_Hut_b3j4': get_hist_regex('{0}_h_DNN_j4b3_{1}'.format(DNN_Hut_hist_name, channel_mapping[channel])),
        'DNN_Hut_b4j4': get_hist_regex('{0}_h_DNN_j4b4_{1}'.format(DNN_Hut_hist_name, channel_mapping[channel])),
        }

discriminants = { # 'name of datacard' : list of tuple with (dicriminant ID, name in 'individual_discriminants' dictionary above). Make sure the 'name of datacard' ends with '_categoryName (for plot step)
    "DNN_Hct_b2j3" : [(1, 'DNN_Hct_b2j3')],
    "DNN_Hct_b2j4" : [(1, 'DNN_Hct_b2j4')],
    "DNN_Hct_b3j3" : [(1, 'DNN_Hct_b3j3')],
    "DNN_Hct_b3j4" : [(1, 'DNN_Hct_b3j4')],
    "DNN_Hct_b4j4" : [(1, 'DNN_Hct_b4j4')],
    "DNN_Hct_all" : [(1, 'DNN_Hct_b2j3'), (2, 'DNN_Hct_b2j4'), (3, 'DNN_Hct_b3j3'), (4, 'DNN_Hct_b3j4'), (5, 'DNN_Hct_b4j4')],
    "DNN_Hut_b2j3" : [(1, 'DNN_Hut_b2j3')],
    "DNN_Hut_b2j4" : [(1, 'DNN_Hut_b2j4')],
    "DNN_Hut_b3j3" : [(1, 'DNN_Hut_b3j3')],
    "DNN_Hut_b3j4" : [(1, 'DNN_Hut_b3j4')],
    "DNN_Hut_b4j4" : [(1, 'DNN_Hut_b4j4')],
    "DNN_Hut_all" : [(1, 'DNN_Hut_b2j3'), (2, 'DNN_Hut_b2j4'), (3, 'DNN_Hut_b3j3'), (4, 'DNN_Hut_b3j4'), (5, 'DNN_Hut_b4j4')],
    #key does matter when removeing qcd-relavant discriminant below
    }
if options.removeHutb4j4:
    del individual_discriminants['DNN_Hut_b4j4']
    del discriminants['DNN_Hut_b4j4']
    discriminants["DNN_Hut_all"].remove((5, 'DNN_Hut_b4j4'))

# IF you change Bkg Def, don't forget to change also the backgrounds list in main and the systematics for cross sections
# ~Kirill definition of Bkg
if options.dataYear != '2016':
    processes_mapping = { # Dict with { key(human friendly name of your choice) : value(regex to find rootfile) }. Be carefull not to match too many files with the regex!
                          # Data !Must! contain 'data_%channels' in the key and MC must not have data in the key
            # Background
            ## TT Semileptonic 
            'ttlf': ['hist_TTpowhegttlf.root', 'hist_TTLLpowhegttlf.root', 'hist_TTHadpowhegttlf.root'],
            'ttcc': ['hist_TTpowhegttcc.root', 'hist_TTLLpowhegttcc.root', 'hist_TTHadpowhegttcc.root'],
            'ttbb': ['hist_TTpowhegttbb.root', 'hist_TTLLpowhegttbb.root', 'hist_TTHadpowhegttbb.root'],
            ## Other Bkg
            'other' : ['hist_TTWJetsToLNu.root', 'hist_TTWJetsToQQ.root', 'hist_TTZToLLNuNu.root', 'hist_TTZToQQ.root', 'hist_W1JetsToLNu.root', 'hist_W2JetsToLNu.root', 'hist_W3JetsToLNu.root', 'hist_W4JetsToLNu.root', 'hist_DYJets*', 'hist_WW.root', 'hist_WZ.root', 'hist_ZZ.root', 'hist_ttHTobb.root', 'hist_ttHToNonbb.root', '.*SingleT.*'],
            # Signal
            'Hut': ['TTTH1L3BaTLepHut', 'TTTH1L3BTLepHut', 'STTH1L3BHut'],
            'Hct': ['TTTH1L3BaTLepHct', 'TTTH1L3BTLepHct', 'STTH1L3BHct'],
            'qcd': ['hist_QCD*'],
            # Data
            'data_el' : ['SingleElectronRun%s'%options.dataYear],
            'data_mu' : ['SingleMuonRun%s'%options.dataYear],
            'data_all' : ['Single.*Run%s'%options.dataYear],
            }
    processes_mapping['data_obs'] = processes_mapping['data_%s'%channel]
    processes_mapping.pop('data_el')
    processes_mapping.pop('data_mu')
    processes_mapping.pop('data_all')
else:
    processes_mapping = { # Dict with { key(human friendly name of your choice) : value(regex to find rootfile) }. Be carefull not to match too many files with the regex!
                          # Data !Must! contain 'data_%channels' in the key and MC must not have data in the key
            # Background
            ## TT Semileptonic 
            'ttlf': ['ttlf.root'],
            'ttcc': ['ttcc.root'],
            'ttbb': ['ttbb.root'],
            ## Other Bkg
            'other' : ['other.root'],
            # Signal
            'Hut': ['sig_stop_Hut.root', 'sig_ttbar_Hut.root'],
            'Hct': ['sig_stop_Hct.root', 'sig_ttbar_Hct.root'],
            # Data
            'data_obs' : ['data_obs.root'],
            }


smTTlist = ['ttlf', 'ttcc', 'ttbb'] # for systematics affecting only SM tt

if options.applyxsec:
    # Read Xsec file
    with open(options.xsecfile, 'r') as xsec_file:
        xsec_data = yaml.load(xsec_file)
    if not xsec_data:
        print "Error loading the cross section file %s"%options.xsecfile
        sys.exit(1)
    
def main():
    """Main function"""
    signals = ['Hut', 'Hct']
    backgrounds = ['ttlf', 'ttcc', 'ttbb', 'other', 'qcd']
    #backgrounds = ['ttlf', 'ttcc', 'ttbb', 'other']
    if options.dataYear == '2016': backgrounds.remove('qcd')
    print "Background considered: ", backgrounds

    for signal in signals:
        dicriminants_per_signal = dict((key,value) for key, value in discriminants.iteritems() if signal in key)
        for discriminant in dicriminants_per_signal.keys() :
            prepareShapes(backgrounds, [signal], dicriminants_per_signal[discriminant], discriminant)

def merge_histograms(process, histogram, destination):
    """
    Merge two histograms together. If the destination histogram does not exist, it
    is created by cloning the input histogram

    Parameters:

    process         Name of the current process
    histogram       Pointer to TH1 to merge
    destination     Dict of destination histograms. The key is the current category.

    Return:
    The merged histogram
    """

    if not histogram:
        raise Exception('Missing histogram for %r. This should not happen.' % process)

    #if histogram.GetEntries() == 0:
    #    return

    # Rescale histogram to luminosity, if it's not data
    if not 'data' in process:
        #print "Rescaleing %s to lumi: "%process, options.luminosity
        histogram.Scale(options.luminosity)
    #print process, " ", histogram.GetTitle(), " ", destination, " ", histogram.GetNbinsX()
    if options.rebinning <= 40: #We have 40 bins!
        #histogram.Rebin(options.rebinning)
        #pass

        #import array
        #arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0., 0.2, 0.4, 0.6, 1.0])
        #arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0., 0.2, 0.4, 0.6, 0.8, 1.0])
        #if 'j3b3' in histogram.GetName(): arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0., 0.2, 0.4, 1.0])
        #if 'j3b3' in histogram.GetName(): arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0., 0.2, 0.4, 0.6, 1.0])
        #else: arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0., 0.2, 0.4, 0.6, 1.0])
        #histogram = histogram.Rebin(len(arr)-1, histogram.GetName(), arr)

        #if any(h_ in histogram.GetName() for h_ in ['j3b2','j4b2']): histogram.Rebin(options.rebinning)
        #if any(h_ in histogram.GetName() for h_ in ['j3b2','j4b2']): histogram.Rebin(4)
        #else: histogram.Rebin(options.rebinning)

        if options.dataYear != '2016':
          import array
          if   'j3b2' in histogram.GetName(): arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0])
          elif 'j4b2' in histogram.GetName(): arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1.0])
          elif 'j3b3' in histogram.GetName(): arr = array.array('d',[-1., -0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 1.0])
          elif 'j4b3' in histogram.GetName(): arr = array.array('d',[-1., -0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.75, 1.0])
          elif 'j4b4' in histogram.GetName(): arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 1.0])
          histogram = histogram.Rebin(len(arr)-1, histogram.GetName(), arr)

    else:
        import array
        arr = array.array('d',[-1., -0.8, -0.6, -0.4, -0.2, 0., 0.2, 0.4, 0.6, 0.8, 1.0])
        histogram = histogram.Rebin(len(arr)-1, histogram.GetName(), arr)

    #if 'ttbb' in process: histogram.Scale(1.23)
    #elif 'ttcc' in process: histogram.Scale(0.81)

    d = destination
    if not d:
        d = histogram.Clone()
        d.SetDirectory(ROOT.nullptr)
    else:
        d.Add(histogram)
    setNegativeBinsToZero(d, process)

    return d


def prepareFile(processes_map, categories_map, root_path, discriminant):
    """
    Prepare a ROOT file suitable for Combine Harvester.

    The structure is the following:
      1) Each observable is mapped to a subfolder. The name of the folder is the name of the observable
      2) Inside each folder, there's a bunch of histogram, one per background and signal hypothesis. The name of the histogram is the name of the background.
    """

    import re

    print("Preparing ROOT file for %s..."%discriminant)

    output_filename = os.path.join(options.output, 'shapes_%s.root' % (discriminant))
    if not os.path.exists(os.path.dirname(output_filename)):
        os.makedirs(os.path.dirname(output_filename))

    files = [os.path.join(root_path, f) for f in os.listdir(root_path) if f.endswith('.root')]

    # Gather a list of inputs files for each process.
    # The key is the process identifier, the value is a list of files
    # If more than one file exist for a given process, the histograms of each file will
    # be merged together later
    processes_files = {}
    for process, paths in processes_map.items():
        process_files = []
        for path in paths:
            r = re.compile(path, re.IGNORECASE)
            process_files += [f for f in files if r.search(f)]
        if len(process_files) == 0:
          print 'Warning: no file found for %s'%process
        processes_files[process] = process_files
        print "Files found for %s: "%(process), [os.path.basename(filename) for filename in process_files]

    # Create the list of histograms (nominal + systematics) for each category
    # we are interested in.
    # The key is the category name, and the value is a list of histogram. The list will always
    # contain at least one histogram (the nominal histogram), and possibly more, two per systematic (up & down variation)
    histogram_names = {}
    for discriminant_tuple in categories_map[discriminant]:
        discriminant_name = discriminant_tuple[1]
        r = re.compile(individual_discriminants[discriminant_name], re.IGNORECASE)
        #f = ROOT.TFile.Open(processes_files.values()[0][0])
        f = ROOT.TFile.Open(processes_files['ttlf'][0])
        histogram_names[discriminant_name] = [n.GetName() for n in f.GetListOfKeys() if r.search(n.GetName())]
        f.Close()

    #for category, histogram_name in categories_map.items():
    #    r = re.compile(histogram_name, re.IGNORECASE)
    #    f = ROOT.TFile.Open(processes_files.values()[0][0])
    #    histogram_names[category] = [n.GetName() for n in f.GetListOfKeys() if r.search(n.GetName())]
    #    f.Close()

    # Extract list of systematics from the list of histograms derived above
    # This code assumes that *all* categories contains the same systematics (as it should)
    # The systematics list is extracted from the histogram list of the first category
    # The list of expanded histogram name is also extract (ie, regex -> full histogram name)
    systematics = set()
    histograms = {}
    systematics_regex = re.compile('__(.*)(up|down)$', re.IGNORECASE)
    for category, histogram_names in histogram_names.items():
        for histogram_name in histogram_names:
            m = systematics_regex.search(histogram_name)
            if m:
                # It's a systematic histogram
                systematics.add(m.group(1))
            else:
                nominal_name = histogram_name
                if category in histograms:
                    # Check that the regex used by the user only match 1 histogram
                    if histograms[category] != nominal_name:
                        raise Exception("The regular expression used for category %r matches more than one histogram: %r and %r" % (category, nominal_name, histograms[category]))
                histograms[category] = nominal_name
    print "Found the following systematics in rootfiles: ", systematics
    if options.sysToAvoid:
        for sysToAvoid in options.sysToAvoid:
            systematics.discard(sysToAvoid)
        print "After ignoring the one mentioned with sysToAvoid option: ", systematics

    cms_systematics = [CMSNamingConvention(s) for s in systematics]

    def dict_get(dict, name):
        if name in dict:
            return dict[name]
        else:
            return None

    # Create final shapes
    shapes = {}
    for category, original_histogram_name in histograms.items():
        shapes[category] = {}
        for process, process_files in processes_files.items():
            shapes[category][process] = {}

            for process_file in process_files:
                f = ROOT.TFile.Open(process_file)
                TH1 = f.Get(original_histogram_name)
                process_file_basename = os.path.basename(process_file)
                if not TH1:
                    print "No histo named %s in %s. Exitting..."%(original_histogram_name, process_file)
                    sys.exit()
                if options.applyxsec and not 'data' in process:
                    xsec = xsec_data[process_file_basename]['cross-section']
                    nevt = xsec_data[process_file_basename]['generated-events']
                    #print "Applying cross sec and nevt on %s "%process_file_basename, xsec, " ", nevt, " --> ", xsec/float(nevt)
                    TH1.Scale(xsec/float(nevt))
                shapes[category][process]['nominal'] = merge_histograms(process, TH1, dict_get(shapes[category][process], 'nominal'))
                if not "data" in process: 
                    for systematic in systematics:
                        if systematic in [item for item in options.sysForSMtt if item not in options.sysForSig] \
                            and not process in smTTlist: continue
                        if systematic in options.sysForSig and not process in ['Hut','Hct']+smTTlist: continue
                        for variation in ['up', 'down']:
                            key = CMSNamingConvention(systematic) + variation.capitalize()
                            #print "Key: ", key
                            TH1_syst = f.Get(original_histogram_name + '__' + systematic + variation)
                            #if systematic in options.sysForSMtt and not process in smTTlist:
                            #    # Copy nominal TH1 in non SMtt processes for systematics affecting only SMtt (already scaled)
                            #    shapes[category][process][key] = merge_histograms(process, TH1, dict_get(shapes[category][process], key))
                            #    continue
                            if not TH1_syst:
                                print "No histo named %s in %s"%(original_histogram_name + '__' + systematic + variation, process_file_basename)
                                sys.exit()
                            if options.applyxsec and not 'data' in process:
                                #process_file_basename = os.path.basename(process_file)
                                #xsec = xsec_data[process_file_basename]['cross-section']
                                #nevt = xsec_data[process_file_basename]['generated-events']
                                TH1_syst.Scale(xsec/float(nevt))
                            shapes[category][process][key] = merge_histograms(process, TH1_syst, dict_get(shapes[category][process], key))
                f.Close()

    output_file = ROOT.TFile.Open(output_filename, 'recreate')

    for category, processes in shapes.items():
        output_file.mkdir(category).cd()
        for process, systematics_ in processes.items():
            for systematic, histogram in systematics_.items():
                histogram.SetName(process if systematic == 'nominal' else process + '__' + systematic)
                histogram.Write()
        output_file.cd()

    output_file.Close()
    print("Done. File saved as %r" % output_filename)

    return output_filename, cms_systematics

def prepareShapes(backgrounds, signals, discriminant, discriminantName):
    # Backgrounds is a list of string of the considered backgrounds corresponding to entries in processes_mapping 
    # Signals is a list of string of the considered signals corresponding to entries in processes_mapping 
    # discriminant is the corresponding entry in the dictionary discriminants 

    import CombineHarvester.CombineTools.ch as ch
    root_path = options.root_path

    file, systematics = prepareFile(processes_mapping, discriminants, root_path, discriminantName)
    if options.dataYear != '2016':
        call(['python', 'symmetrize.py', options.output, file, options.dataYear], shell=False)
    
    for signal in signals :
        cb = ch.CombineHarvester()
        cb.AddObservations(['*'], [''], ['_%s'%options.dataYear], [''], discriminant)
        cb.AddProcesses(['*'], [''], ['_%s'%options.dataYear], [''], [signal], discriminant, True)
        #cb.AddProcesses(['*'], [''], ['_%s'%options.dataYear], [''], backgrounds, discriminant, False)
        if options.dataYear == '2016':
            cb.AddProcesses(['*'], [''], ['_%s'%options.dataYear], [''], backgrounds, discriminant, False)
        else:
            if not 'b2j3' in discriminantName:
                try: backgrounds.remove('qcd')
                except: pass
            else:
                if not 'qcd' in backgrounds: backgrounds.append('qcd')
            if 'all' in discriminantName:
                if signal == 'Hut':
                    discriminant.remove((1, 'DNN_Hut_b2j3'))
                    cb.AddProcesses(['*'], [''], ['_%s'%options.dataYear], [''], backgrounds+['qcd'], [(1,'DNN_Hut_b2j3')], False)
                else:
                    discriminant.remove((1, 'DNN_Hct_b2j3'))
                    cb.AddProcesses(['*'], [''], ['_%s'%options.dataYear], [''], backgrounds+['qcd'], [(1,'DNN_Hct_b2j3')], False)
                cb.AddProcesses(['*'], [''], ['_%s'%options.dataYear], [''], backgrounds, discriminant, False)
                if signal == 'Hut': discriminant.append((1, 'DNN_Hut_b2j3'))
                else:               discriminant.append((1, 'DNN_Hct_b2j3'))
            else:
                cb.AddProcesses(['*'], [''], ['_%s'%options.dataYear], [''], backgrounds, discriminant, False)

        # Systematics
        if not options.nosys:
            for systematic in systematics:
                systematic_only_for_SMtt = False
                systematic_only_for_Sig = False

                for systSMtt in options.sysForSMtt:
                    if CMSNamingConvention(systSMtt) == systematic:
                        systematic_only_for_SMtt = True
                for systSig in options.sysForSig:
                    if CMSNamingConvention(systSig) == systematic:
                        systematic_only_for_Sig = True

                if not systematic_only_for_SMtt and not systematic_only_for_Sig:
                    cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap()(1.00))
                elif systematic_only_for_SMtt and not systematic_only_for_Sig:
                    cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('process')(smTTlist, 1.00))
                    #if 'hdamp' in systematic:
                    #    for i in xrange(len(discriminant)):
                    #        if 'b2j3' in discriminant[i][1]:
                    #            cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttlf'], 1.00))
                    #            cb.cp().AddSyst(cb, systematic, 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb','ttcc'], 1.05))
                    #        elif 'b2j4' in discriminant[i][1]:
                    #            cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('bin', 'process')([discriminant[i][1]], smTTlist, 1.00))
                    #        elif 'b3j3' in discriminant[i][1]:
                    #            cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttlf'], 1.00))
                    #            cb.cp().AddSyst(cb, systematic, 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb','ttcc'], 1.05))
                    #        elif 'b3j4' in discriminant[i][1]:
                    #            cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('bin', 'process')([discriminant[i][1]], smTTlist, 1.00))
                    #        elif 'b4j4' in discriminant[i][1]:
                    #            cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.00))
                    #            cb.cp().AddSyst(cb, systematic, 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc','ttlf'], 1.05))
                    #else: cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('process')(smTTlist, 1.00))
                elif not systematic_only_for_SMtt and systematic_only_for_Sig:
                    cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('process')([signal], 1.00))
                else:
                    cb.cp().AddSyst(cb, systematic, 'shape', ch.SystMap('process')(smTTlist+[signal], 1.00))

            #Lumi corr. https://twiki.cern.ch/twiki/bin/view/CMS/TWikiLUM#LumiComb
            #cb.cp().AddSyst(cb, 'CMS_lumi', 'lnN', ch.SystMap()(options.luminosityError))
            if options.dataYear == '2016':
                cb.cp().AddSyst(cb, 'CMS_lumi_uncorr_2016', 'lnN', ch.SystMap()(1.01))
                cb.cp().AddSyst(cb, 'CMS_lumi_corr_161718', 'lnN', ch.SystMap()(1.006))
                #reproducing 2016
                #cb.cp().AddSyst(cb, 'CMS_lumi_uncorr_2016', 'lnN', ch.SystMap()(1.027))
            elif options.dataYear == '2017':
                cb.cp().AddSyst(cb, 'CMS_lumi_uncorr_2017', 'lnN', ch.SystMap()(1.02))
                cb.cp().AddSyst(cb, 'CMS_lumi_corr_161718', 'lnN', ch.SystMap()(1.009))
                cb.cp().AddSyst(cb, 'CMS_lumi_corr_1718', 'lnN', ch.SystMap()(1.006))
            elif options.dataYear == '2018':
                cb.cp().AddSyst(cb, 'CMS_lumi_uncorr_2018', 'lnN', ch.SystMap()(1.015))
                cb.cp().AddSyst(cb, 'CMS_lumi_corr_161718', 'lnN', ch.SystMap()(1.02))
                cb.cp().AddSyst(cb, 'CMS_lumi_corr_1718', 'lnN', ch.SystMap()(1.002))

            cb.cp().AddSyst(cb, 'tt_xsec', 'lnN', ch.SystMap('process')(['ttbb', 'ttcc', 'ttlf'], 1.055))
            cb.cp().AddSyst(cb, 'Other_xsec', 'lnN', ch.SystMap('process')(['other'], 1.1))
            #cb.cp().AddSyst(cb, 'hdamp', 'lnN', ch.SystMap('process')(smTTlist, 1.05))
            #cb.cp().AddSyst(cb, 'TuneCP5', 'lnN', ch.SystMap('process')(smTTlist, 1.03))

            for i in xrange(len(discriminant)):
                if 'b2j3' in discriminant[i][1]:
                    cb.cp().AddSyst(cb, '$PROCESS_norm', 'lnN', ch.SystMap('process')(['qcd'], 1.5))
                #reproducing 2016 ### comment out Other_xsec above!
                #if 'b2j3' in discriminant[i][1]: cb.cp().AddSyst(cb, 'Other_xsec_b2j3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['other'], 1.1))
                #if 'b2j4' in discriminant[i][1]: cb.cp().AddSyst(cb, 'Other_xsec_b2j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['other'], 1.1))
                #if 'b3j3' in discriminant[i][1]: cb.cp().AddSyst(cb, 'Other_xsec_b3j3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['other'], 1.1))
                #if 'b3j4' in discriminant[i][1]: cb.cp().AddSyst(cb, 'Other_xsec_b3j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['other'], 1.1))
                #if 'b4j4' in discriminant[i][1]: cb.cp().AddSyst(cb, 'Other_xsec_b4j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['other'], 1.1))

            if options.dataYear == '2016':
                #reproducing 2016
                #cb.cp().AddSyst(cb, 'hdamp_2016', 'lnN', ch.SystMap('process')(['ttbb', 'ttcc', 'ttlf'], 1.05))
                #cb.cp().AddSyst(cb, 'scale_2016', 'lnN', ch.SystMap('process')(['ttbb', 'ttcc', 'ttlf'], 1.15))
                #for i in xrange(len(discriminant)):
                #    if 'j3' in discriminant[i][1]:
                #        cb.cp().AddSyst(cb, '$PROCESS_norm_j3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.5))
                #        cb.cp().AddSyst(cb, '$PROCESS_norm_j3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                #        cb.cp().AddSyst(cb, 'jec_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb', 'ttcc', 'ttlf', 'other', signal], 1.01))
                #    else:
                #        cb.cp().AddSyst(cb, '$PROCESS_norm_j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.5))
                #        cb.cp().AddSyst(cb, '$PROCESS_norm_j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                #        cb.cp().AddSyst(cb, 'jec_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb', 'ttcc', 'ttlf', 'other', signal], 1.05))#1.05 for j4
                for i in xrange(len(discriminant)):
                    if 'b2' in discriminant[i][1]:
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b2_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.3))
                        #cb.cp().AddSyst(cb, '$PROCESS_norm_b2_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b2', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                    elif 'b3' in discriminant[i][1]:
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b3_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.3))
                        #cb.cp().AddSyst(cb, '$PROCESS_norm_b3_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                    elif 'b4' in discriminant[i][1]:
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b4_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.3))
                        #cb.cp().AddSyst(cb, '$PROCESS_norm_b4_2016', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
            else:
                for i in xrange(len(discriminant)):
                    if 'b2' in discriminant[i][1]:
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b2', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.2))
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b2', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                    elif 'b3' in discriminant[i][1]:
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.22))
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                    elif 'b4' in discriminant[i][1]:
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.2))
                        cb.cp().AddSyst(cb, '$PROCESS_norm_b4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))

                #if 'j3' in discriminant[i][1]:
                #    #cb.cp().AddSyst(cb, '$PROCESS_norm_j3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.5))
                #    cb.cp().AddSyst(cb, '$PROCESS_norm_j3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.3))
                #    cb.cp().AddSyst(cb, '$PROCESS_norm_j3', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))
                #else:
                #    #cb.cp().AddSyst(cb, '$PROCESS_norm_j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.5))
                #    cb.cp().AddSyst(cb, '$PROCESS_norm_j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttbb'], 1.3))
                #    cb.cp().AddSyst(cb, '$PROCESS_norm_j4', 'lnN', ch.SystMap('bin', 'process')([discriminant[i][1]], ['ttcc'], 1.5))

        # Import shapes from ROOT file
        cb.cp().backgrounds().ExtractShapes(file, '$BIN/$PROCESS', '$BIN/$PROCESS__$SYSTEMATIC')
        cb.cp().signals().ExtractShapes(file, '$BIN/$PROCESS', '$BIN/$PROCESS__$SYSTEMATIC')

        #reproducing 2016 - comment out
        if options.dataYear == '2016':
            rebin = ch.AutoRebin().SetBinThreshold(100).SetBinUncertFraction(0.1)
            rebin.Rebin(cb.cp(), cb)

        #elif options.dataYear == '2017':
        #    #rebin_b2j3 = ch.AutoRebin().SetBinThreshold(5400)#.SetBinUncertFraction(0.1)
        #    #rebin_b2j3.Rebin(cb.cp().bin(["DNN_Hut_b2j3", "DNN_Hct_b2j3"]), cb)

        #AutoMCStat
        cb.SetAutoMCStats(cb, 0.1)
        #reproducing 2016
        #print "Treating bbb"
        #bbb = ch.BinByBinFactory()
        #bbb.SetAddThreshold(0.0001)
        #bbb.AddBinByBin(cb.cp().backgrounds(), cb)
        #bbb.AddBinByBin(cb.cp().signals(), cb)

        output_prefix = 'FCNC_%s_Discriminant_%s' % (signal, discriminantName)

        output_dir = os.path.join(options.output, '%s' % (signal))
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        fake_mass = '125'

        # Write card
        datacard = os.path.join(output_dir, output_prefix + '.dat')
        cb.cp().mass([fake_mass, "*"]).WriteDatacard(os.path.join(output_dir, output_prefix + '.dat'), os.path.join(output_dir, output_prefix + '_shapes.root'))

        # Write small script to compute the limit
        workspace_file = os.path.basename(os.path.join(output_dir, output_prefix + '_combine_workspace.root'))
        script = """#! /bin/bash

text2workspace.py {datacard} -m {fake_mass} -o {workspace_root}

# Run limit

echo combine -M AsymptoticLimits -n {name} {workspace_root} -S {systematics} #--run blind #-v +2
#combine -M AsymptoticLimits -n {name} {workspace_root} -S {systematics} #--run expected #-v +2
combine -M AsymptoticLimits -n {name} {workspace_root} -S {systematics} #--run blind #-v +2
#combine -H AsymptoticLimits -M HybridNew -n {name} {workspace_root} -S {systematics} --LHCmode LHC-limits --expectedFromGrid 0.5 #for ecpected, use 0.84 and 0.16
""".format(workspace_root=workspace_file, datacard=os.path.basename(datacard), name=output_prefix, fake_mass=fake_mass, systematics=(0 if options.nosys else 1))
        script_file = os.path.join(output_dir, output_prefix + '_run_limits.sh')
        with open(script_file, 'w') as f:
            f.write(script)
        
        st = os.stat(script_file)
        os.chmod(script_file, st.st_mode | stat.S_IEXEC)


        # Write small script for datacard checks
        script = """#! /bin/bash

# Run checks
echo combine -M FitDiagnostics -t -1 --expectSignal 0 {datacard} -n fitDiagnostics_{name}_bkgOnly -m 125 --robustHesse 1 --robustFit=1 --rMin -20 --rMax 20 #--plots
echo python ../../../../HiggsAnalysis/CombinedLimit/test/diffNuisances.py -a fitDiagnostics_{name}_bkgOnly.root -g fitDiagnostics_{name}_bkgOnly_plots.root
combine -M FitDiagnostics -t -1 --expectSignal 0 {datacard} -n _{name}_bkgOnly -m 125 --robustHesse 1 --robustFit=1 --rMin -20 --rMax 20 #--plots
python ../../../../HiggsAnalysis/CombinedLimit/test/diffNuisances.py -a fitDiagnostics_{name}_bkgOnly.root -g fitDiagnostics_{name}_bkgOnly_plots.root --skipFitS > fitDiagnostics_{name}_bkgOnly.log
python ../../printPulls.py fitDiagnostics_{name}_bkgOnly_plots.root
combine -M FitDiagnostics -t -1 --expectSignal 1 {datacard} -n _{name}_bkgPlusSig -m 125 --robustHesse 1 --robustFit=1 --rMin -20 --rMax 20 #--plots
python ../../../../HiggsAnalysis/CombinedLimit/test/diffNuisances.py -a fitDiagnostics_{name}_bkgPlusSig.root -g fitDiagnostics_{name}_bkgPlusSig_plots.root --skipFitB > fitDiagnostics_{name}_bkgPlusSig.log
python ../../printPulls.py fitDiagnostics_{name}_bkgPlusSig_plots.root

#print NLL for check
combineTool.py -M FastScan -w {name}_combine_workspace.root:w -o {name}_nll
""".format(workspace_root=workspace_file, datacard=os.path.basename(datacard), name=output_prefix, fake_mass=fake_mass, systematics=(0 if options.nosys else 1))
        script_file = os.path.join(output_dir, output_prefix + '_run_closureChecks.sh')
        with open(script_file, 'w') as f:
            f.write(script)
        
        st = os.stat(script_file)
        os.chmod(script_file, st.st_mode | stat.S_IEXEC)

        # Write small script for impacts
        script = """#! /bin/bash

# Run impacts
combineTool.py -M Impacts -d {name}_combine_workspace.root -m 125 --doInitialFit --robustFit=1 --robustHesse 1 --rMin -20 --rMax 20 -t -1
combineTool.py -M Impacts -d {name}_combine_workspace.root -m 125 --robustFit=1 --robustHesse 1 --doFits --rMin -20 --rMax 20 -t -1 --parallel 32
combineTool.py -M Impacts -d {name}_combine_workspace.root -m 125 -o {name}_expected_impacts.json --rMin -20 --rMax 20 -t -1
plotImpacts.py -i {name}_expected_impacts.json -o {name}_expected_impacts --per-page 50

combineTool.py -M Impacts -d {name}_combine_workspace.root -m 125 --doInitialFit --robustFit=1 --robustHesse 1 --rMin -20 --rMax 20
combineTool.py -M Impacts -d {name}_combine_workspace.root -m 125 --robustFit=1 --doFits --robustHesse 1 --rMin -20 --rMax 20 --parallel 32
combineTool.py -M Impacts -d {name}_combine_workspace.root -m 125 -o {name}_impacts.json --rMin -20 --rMax 20
plotImpacts.py -i {name}_impacts.json -o {name}_impacts --per-page 50
""".format(workspace_root=workspace_file, datacard=os.path.basename(datacard), name=output_prefix, fake_mass=fake_mass, systematics=(0 if options.nosys else 1))
        script_file = os.path.join(output_dir, output_prefix + '_run_impacts.sh')
        with open(script_file, 'w') as f:
            f.write(script)
        
        st = os.stat(script_file)
        os.chmod(script_file, st.st_mode | stat.S_IEXEC)

        # Write small script for postfit shapes
        script = """#! /bin/bash

# Run postfit
echo combine -M FitDiagnostics {datacard} -n _{name}_postfit --saveNormalizations --saveShapes --saveWithUncertainties --preFitValue 0 --rMin -20 --rMax 20 --robustHesse 1 --robustFit=1 -v 1
combine -M FitDiagnostics {datacard} -n _{name}_postfit --saveNormalizations --saveShapes --saveWithUncertainties --preFitValue 0 --rMin -20 --rMax 20 --robustHesse 1 --robustFit=1 -v 1 #--plots
PostFitShapesFromWorkspace -w {name}_combine_workspace.root -d {datacard} -o postfit_shapes_{name}.root -f fitDiagnostics_{name}_postfit.root:fit_b --postfit --sampling
python ../../convertPostfitShapesForPlotIt.py -i postfit_shapes_{name}.root
$CMSSW_BASE/src/UserCode/HEPToolsFCNC/plotIt/plotIt -o postfit_shapes_{name}_forPlotIt ../../postfit_plotIt_config_{coupling}_{year}.yml -y
$CMSSW_BASE/src/UserCode/HEPToolsFCNC/plotIt/plotIt -o postfit_shapes_{name}_forPlotIt ../../postfit_plotIt_config_{coupling}_{year}_qcd.yml -y
""".format(workspace_root=workspace_file, datacard=os.path.basename(datacard), name=output_prefix, fake_mass=fake_mass, systematics=(0 if options.nosys else 1), coupling=("Hut" if "Hut" in output_prefix else "Hct"), year=options.dataYear)
        script_file = os.path.join(output_dir, output_prefix + '_run_postfit.sh')
        with open(script_file, 'w') as f:
            f.write(script)
        
        st = os.stat(script_file)
        os.chmod(script_file, st.st_mode | stat.S_IEXEC)

def CMSNamingConvention(syst):
    # Taken from https://twiki.cern.ch/twiki/bin/view/CMS/HiggsWG/HiggsCombinationConventions
    # systlist = ['jec', 'jer', 'elidiso', 'muidiso', 'jjbtag', 'pu', 'trigeff']
    #if syst not in options.correlatedSys:
    if syst not in correlatedSys:
        return 'CMS_' + options.dataYear + '_' + syst
    else:
        return 'CMS_' + syst

if __name__ == '__main__':
    main()

