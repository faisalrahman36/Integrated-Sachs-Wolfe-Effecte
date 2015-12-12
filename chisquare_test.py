#! /usr/bin/env python
"""
  NAME:
    chisquare_test.py
  PURPOSE:
    Program to check that T*C^-1*T follows chi square distribution as expected
  USES:
    make_Cmatrix.py
  MODIFICATION HISTORY:
    Written by Z Knight, 2015.11.30
    Added C matrix correction routine; ZK 2015.12.08
    Switched to Cholesky Decomposition Inverse; ZK, 2015.12.11
    Added useMicro, doBeamSmooth, doPixWin parameters; ZK, 2015.12.11

"""

import numpy as np
import matplotlib.pyplot as plt
import healpy as hp
import time  # for measuring duration
import make_Cmatrix as mcm


def test(case = 1,nTrials=1000):
    """
        function for testing the expectation value <T*C**-1*T> = N_pix
        case: selects which set of files to use for test
        nTrials: the number of random skies to use
    """

    # get Cl
    ISWoutFile = 'ISWout_scalCls.fits'
    ell, temps = mcm.getCl(ISWoutFile) # temps has units K**2

    # show Cl
    # mcm.showCl(ell,temps)

    # dictionary of sets of file names
    PSG = '/Data/PSG/'
    fileSets = {
    100:(PSG+'ten_point/ISWmask_din1_R010.fits','covar6110_R010_nhp.npy','invCovar_R010_nhp.npy'), #LU; lmax250, with BW
    101:(PSG+'ten_point/ISWmask_din1_R010.fits','covar6110_R010_nhp.npy','invCovar_R010_RD.npy'), #RD; lmax250, with BW
    102:(PSG+'ten_point/ISWmask_din1_R010.fits','covar6110_R010_nhp.npy','invCovar_R010_cho.npy'), #cho; lmax250, with BW
    1:(PSG+'small_masks/ISWmask_din1_R010_trunc1000.fits','covar1000b.npy','invCovar1000b.npy'), #lmax250
    2:(PSG+'small_masks/ISWmask_din1_R010_trunc1000.fits','covar1000c.npy','invCovar1000c.npy'), #lmax2000
    3:(PSG+'small_masks/ISWmask_din1_R010_trunc1000.fits','covar1000d.npy','invCovar1000d.npy'), #lmax250, with W
    4:(PSG+'small_masks/ISWmask_din1_R010_trunc1000.fits','covar1000e.npy','invCovar1000e.npy'), #lmax250, with B
    5:(PSG+'small_masks/ISWmask_din1_R010_trunc1000.fits','covar1000f.npy','invCovar1000f.npy'), #lmax250, no BW
    7:(PSG+'small_masks/ISWmask_din1_R060_trunc1.fits','covar478a.npy','invCovar478a.npy'), #lmax2000, no BW
    8:(PSG+'small_masks/ISWmask_din1_R060_trunc2.fits','covar525a.npy','invCovar525a.npy'), #lmax2000, no BW
    9:(PSG+'small_masks/ISWmask_din1_R060_trunc3.fits','covar500a.npy','invCovar500a.npy'), #lmax2000, no BW
    10:(PSG+'small_masks/ISWmask_din1_R060_trunc1.fits','covar478b.npy','invCovar478b.npy'), #lmax250, no BW
    11:(PSG+'small_masks/ISWmask_din1_R060_trunc2.fits','covar525b.npy','invCovar525b.npy'), #lmax250, no BW
    12:(PSG+'small_masks/ISWmask_din1_R060_trunc3.fits','covar500b.npy','invCovar500b.npy'), #lmax250, no BW
    13:(PSG+'small_masks/ISWmask_din1_R060_trunc1.fits','covar478c.npy','invCovar478c.npy'), #lmax250, with B
    14:(PSG+'small_masks/ISWmask_din1_R060_trunc2.fits','covar525c.npy','invCovar525c.npy'), #lmax250, with B
    15:(PSG+'small_masks/ISWmask_din1_R060_trunc3.fits','covar500c.npy','invCovar500c.npy') #lmax250, with B

    }

    #case = 0
    maskFile,saveMatrixFile,saveInvCMFile = fileSets.get(case)

    newMatrix = False#True
    useMicro = False#True
    doBeamSmooth = True#False
    doPixWin = False
    useRD = False#True #Overrides useCho
    useCho = True # overrides default: use LU
    if newMatrix:
        startTime = time.time()
        print 'starting C matrix creation...'
        covMat = mcm.makeCmatrix(maskFile, ISWoutFile, highpass=0, beamSmooth=doBeamSmooth,
                                 pixWin=doPixWin, lmax=250, useMicro=useMicro)
        #covMat = mcm.cMatCorrect(covMat) #correction due to estimating mean from sample
        mcm.symSave(covMat, saveMatrixFile)

        if useRD:
            print 'starting eigen decomposition...'
            w, v = np.linalg.eigh(covMat)
            print 'starting RD inversion...'
            invCMat = mcm.RDInvert(w, v)
        elif useCho:
            print 'starting Cholesky inversion...'
            invCMat = mcm.choInvert(covMat)
        else:
            print 'starting LU inversion...'
            invCMat = np.linalg.inv(covMat)
        print 'time elapsed: ', int((time.time() - startTime) / 60), ' minutes'
        np.save(saveInvCMFile, invCMat)

    else:
        # covMat = mcm.symLoad(saveMatrixFile)
        invCMat = np.load(saveInvCMFile)

    # load the mask - nest=True for mask!
    mask = hp.read_map(maskFile, nest=True)

    # apply gaussbeam before synfast?
    #lmax = 250
    #Wpix = hp.pixwin(64)
    #W_l = Wpix[:lmax+1]
    #mbeam = hp.gauss_beam(120./60*np.pi/180,lmax=lmax) # 120 arcmin to be below W_l
    #B_l = mbeam[:lmax+1]
    #temps = temps[:lmax+1]*B_l**2 #*W_l**2

    #nTrials = 1000
    NSIDE=64
    lmax=250
    fwhmMin = 120.
    fwhmRad = fwhmMin/60.*np.pi/180.

    chiSqResults = np.zeros(nTrials)
    for trial in range(nTrials):
        print 'starting trial ',trial+1,' of ',nTrials
        if doBeamSmooth:
            if doPixWin:
                map = hp.synfast(temps, NSIDE, lmax=lmax, fwhm=fwhmRad, pixwin=True)
            else:
                map = hp.synfast(temps, NSIDE, lmax=lmax, fwhm=fwhmRad)
        else:
            if doPixWin:
                map = hp.synfast(temps, NSIDE, lmax=lmax, pixwin=True)
            else:
                map = hp.synfast(temps, NSIDE, lmax=lmax)
        Tvec = map[np.where(mask)] #apply mask
        if useMicro:
            Tvec = Tvec*1e6 #convert K to microK
        chiSqResults[trial] = np.dot(Tvec,np.dot(invCMat,Tvec))
    csqMean = np.mean(chiSqResults)
    print 'average of chiSquared results: ',csqMean
    plt.plot(chiSqResults,linestyle="none",marker='+')
    plt.title('chiSquare test average: '+str(csqMean))
    plt.xlabel('draw number')
    plt.ylabel('chi squared result')
    plt.show()

if __name__ == '__main__':
    test()
