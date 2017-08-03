import os.path
import glob
try:
    import cPickle as pickle
except:
    import pickle
import astropy.units as u
import numpy as np


def gen_summary(run_dir):
    pklfiles = glob.glob(os.path.join(run_dir,'*.pkl'))

    out = {'detected':[],
           'fullspectra':[],
           'partspectra':[],
           'Rps':[],
           'Mps':[],
           'tottime':[],
           'starinds':[],
           'smas':[],
           'ps':[],
           'es':[],
           'WAs':[],
           'SNRs':[],
           'fZs':[],
           'fEZs':[],
           'allsmas':[],
           'allRps':[],
           'allps':[],
           'alles':[],
           'allMps':[],
           'dMags':[],
           'rs':[]}

    for counter,f in enumerate(pklfiles):
        print "%d/%d"%(counter,len(pklfiles))
        with open(f, 'rb') as g:
            res = pickle.load(g)

        dets = np.hstack([row['plan_inds'][row['det_status'] == 1]  for row in res['DRM']])
        out['detected'].append(dets)
        
        out['WAs'].append(np.hstack([row['det_params']['WA'][row['det_status'] == 1].to('arcsec').value for row in res['DRM']]))
        out['dMags'].append(np.hstack([row['det_params']['dMag'][row['det_status'] == 1] for row in res['DRM']]))
        out['rs'].append(np.hstack([row['det_params']['d'][row['det_status'] == 1].to('AU').value for row in res['DRM']]))
        out['fEZs'].append(np.hstack([row['det_params']['fEZ'][row['det_status'] == 1].value for row in res['DRM']]))
        out['fZs'].append(np.hstack([[row['det_fZ'].value]*len(np.where(row['det_status'] == 1)[0]) for row in res['DRM']]))
        out['fullspectra'].append(np.hstack([row['plan_inds'][row['char_status'] == 1]  for row in res['DRM']]))
        out['partspectra'].append(np.hstack([row['plan_inds'][row['char_status'] == -1]  for row in res['DRM']]))
        out['tottime'].append(np.sum([row['det_time'].value+row['char_time'].value for row in res['DRM']]))
        out['SNRs'].append(np.hstack([row['det_SNR'][row['det_status'] == 1]  for row in res['DRM']]))
        out['Rps'].append((res['systems']['Rp'][dets]/u.R_earth).decompose().value)
        out['smas'].append(res['systems']['a'][dets].to(u.AU).value)
        out['ps'].append(res['systems']['p'][dets])
        out['es'].append(res['systems']['e'][dets])
        out['Mps'].append((res['systems']['Mp'][dets]/u.M_earth).decompose())
        out['starinds'].append(np.hstack([[row['star_ind']]*len(np.where(row['det_status'] == 1)[0]) for row in res['DRM']]))

        """
        out['allRps'].append((res['systems']['Rp']/u.R_earth).decompose().value)
        out['allMps'].append((res['systems']['Mp']/u.M_earth).decompose())
        out['allsmas'].append(res['systems']['a'].to(u.AU).value)
        out['allps'].append(res['systems']['p'])
        out['alles'].append(res['systems']['e'])
        """
        
    return out

