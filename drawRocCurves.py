from rocCurveFacility import *
import os, sys
import ROOT
from ROOT import *

gROOT.ProcessLine(".x setTDRStyle.C")

# Script to draw 2016 and 2017 rocCurves on same graph (easy to modifiy for ther purposes)
pathToTh1_2016 = "datacards_201215_2016_norebin"
pathToTh1_2017 = "datacards_201215_2017v6_norebin"
pathToTh1_2018 = "datacards_201215_2018v6_norebin"
output_postfix = ''

if sys.argv[1]: output_postfix = sys.argv[1]

ROOT.gROOT.SetBatch(ROOT.kTRUE)

def getRocCurve(partial_name, th1_rootFileName, coupling):
    th1_rootFile = ROOT.TFile(th1_rootFileName)

    print th1_rootFile.Print()
    print partial_name + "/" + coupling
    print th1_rootFile.Get(partial_name + "/" + coupling)
    
    sig_th1 = th1_rootFile.Get(partial_name + "/" + coupling)
    sig_eff = drawEffVsCutCurve(sig_th1)
    
    ttbb_th1 = th1_rootFile.Get(partial_name + "/ttbb")
    ttlf_th1 = th1_rootFile.Get(partial_name + "/ttlf")
    ttcc_th1 = th1_rootFile.Get(partial_name + "/ttcc")
    other_th1 = th1_rootFile.Get(partial_name + "/other")
    bkg_th1 = ttbb_th1 + ttlf_th1 + ttcc_th1 + other_th1
    bkg_eff = drawEffVsCutCurve(bkg_th1)

    rocCurve = drawROCfromEffVsCutCurves(sig_eff, bkg_eff)
    return rocCurve



rocCurveOutputFolder = 'rocCurves_' + pathToTh1_2016.split('_')[1] + ('_') + pathToTh1_2017.split('_')[1] + ('_') + pathToTh1_2018.split('_')[1] + output_postfix

if not os.path.exists(rocCurveOutputFolder):
    os.mkdir(rocCurveOutputFolder)

couplings = ['Hct', 'Hut']
jetBins = ['b2j3', 'b3j3', 'b2j4', 'b3j4', 'b4j4']

for coupling in couplings:
    for jetBin in jetBins:
        title = "RocCurves_" + coupling  + "_" + jetBin
        canvas = ROOT.TCanvas(title, title, 450,400)
        canvas.SetLeftMargin(0.11)
        #canvas.SetGrid()
        frame = canvas.DrawFrame(0., 0., 1., 1.)

        #Axis
        xaxis = frame.GetXaxis()
        yaxis = frame.GetYaxis()
        xaxis.SetTitle("Background efficiency")
        xaxis.SetTitleOffset(1.0)
        xaxis.SetLabelSize(0.04)
        xaxis.SetLabelFont(42)
        xaxis.SetTitleFont(42)
        xaxis.SetTitleSize(0.05)
        yaxis.SetTitle("Signal efficiency")
        yaxis.SetTitleOffset(1.1)
        yaxis.SetLabelSize(0.04)
        yaxis.SetLabelFont(42)
        yaxis.SetTitleFont(42)
        yaxis.SetTitleSize(0.05)

        partial_name = 'DNN_' + coupling + '_' + jetBin 

        th1_rootFileName_2016 = os.path.join(pathToTh1_2016, 'shapes_' + partial_name + '.root')
        rocCurve_2016 = getRocCurve(partial_name, th1_rootFileName_2016, coupling)
        #rocCurve_2016.SetTitle("ROC Curve: " + coupling + " " + jetBin)
        rocCurve_2016.SetMarkerColor(ROOT.kBlue)
        rocCurve_2016.SetLineColor(ROOT.kBlue)
        rocCurve_2016.SetLineWidth(2)
        #rocCurve_2016.SetMarkerStyle(4)
        rocCurve_2016.Draw()

        th1_rootFileName_2017 = os.path.join(pathToTh1_2017, 'shapes_' + partial_name + '.root')
        rocCurve_2017 = getRocCurve(partial_name, th1_rootFileName_2017, coupling)
        rocCurve_2017.SetMarkerColor(ROOT.kRed)
        rocCurve_2017.SetLineColor(ROOT.kRed)
        rocCurve_2017.SetLineWidth(2)
        #rocCurve_2017.SetMarkerStyle(2)
        rocCurve_2017.Draw("same")

        th1_rootFileName_2018 = os.path.join(pathToTh1_2018, 'shapes_' + partial_name + '.root')
        rocCurve_2018 = getRocCurve(partial_name, th1_rootFileName_2018, coupling)
        rocCurve_2018.SetMarkerColor(8)
        rocCurve_2018.SetLineColor(8)
        rocCurve_2018.SetLineWidth(2)
        #rocCurve_2018.SetMarkerStyle(2)
        rocCurve_2018.Draw("same")
        canvas.RedrawAxis()

        # Some text
        latexLabel = TLatex()
        latexLabel.SetTextSize(0.75 * canvas.GetTopMargin())
        latexLabel.SetNDC()
        #Lumi
        latexLabel.SetTextFont(62) # helvetica
        latexLabel.DrawLatex(0.72, 0.96, '137 fb^{-1} (13 TeV)')
        #CMS
        latexLabel.SetTextFont(62) # helvetica bold face
        latexLabel.SetTextSize(1.00 * canvas.GetTopMargin())
        latexLabel.DrawLatex(0.15, 0.87, "CMS")
        #Suppl
        progress = 'Simulation'
        latexLabel.SetTextFont(52) # helvetica italics
        latexLabel.SetTextSize(0.7 * canvas.GetTopMargin())
        latexLabel.DrawLatex(0.15, 0.82, progress)
        latexLabel.Clear()
        progress = 'Supplementary'
        latexLabel.SetTextFont(52) # helvetica italics
        latexLabel.SetTextSize(0.7 * canvas.GetTopMargin())
        latexLabel.DrawLatex(0.15, 0.79, progress)
        latexLabel.Clear()
        #jetbin
        latexLabel.SetTextFont(42) # helvetica
        latexLabel.SetTextSize(1.00 * canvas.GetTopMargin())
        latexLabel.DrawLatex(0.15, 0.72, coupling + ", " + jetBin)
        latexLabel.Clear()


        legend = ROOT.TLegend(0.7, 0.25, 0.9, 0.45)
        legend.AddEntry(rocCurve_2016, "2016", "l")
        legend.AddEntry(rocCurve_2017, "2017", "l")
        legend.AddEntry(rocCurve_2018, "2018", "l")
        legend.Draw("same")

        canvas.Print(os.path.join(rocCurveOutputFolder, title + ".png"))
        canvas.Print(os.path.join(rocCurveOutputFolder, title + ".pdf"))

