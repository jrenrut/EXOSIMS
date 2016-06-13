# -*- coding: utf-8 -*-
import numpy as np
import numbers
import astropy.units as u
from astropy.coordinates import SkyCoord
from EXOSIMS.util.get_module import get_module
from EXOSIMS.util.deltaMag import deltaMag

class TargetList(object):
    """Target List class template
    
    This class contains all variables and functions necessary to perform 
    Target List Module calculations in exoplanet mission simulation.
    
    It inherits the following class objects which are defined in __init__:
    StarCatalog, OpticalSystem, PlanetPopulation, ZodiacalLight, Completeness
    
    Args:
        \*\*specs:
            user specified values
            
    Attributes:
        OpticalSystem (OpticalSystem):
            OpticalSystem class object
        PlanetPopulation (PlanetPopulation):
            PlanetPopulation class object
        PlanetPhyiscalModel (PlanetPhysicalModel):
            PlanetPhysicalModel class object
        ZodiacalLight (ZodiacalLight):
            ZodiacalLight class object
        Completeness (Completeness):
            Completeness class object
        BackgroundSources (BackgroundSources):
            BackgroundSources class object
        PostProcessing (PostProcessing):
            PostProcessing class object
        StarCatalog (StarCatalog):
            StarCatalog class object (only retained if keepStarCatalog is True)
        Name (ndarray):
            1D numpy ndarray of star names
        Spec (ndarray):
            1D numpy ndarray of star spectral types
        Umag (ndarray):
            1D numpy ndarray of U magnitude
        Bmag (ndarray):
            1D numpy ndarray of B magnitude
        Vmag (ndarray):
            1D numpy ndarray of V magnitude
        Rmag (ndarray):
            1D numpy ndarray of R magnitude
        Imag (ndarray):
            1D numpy ndarray of I magnitude
        Jmag (ndarray):
            1D numpy ndarray of J magnitude
        Hmag (ndarray):
            1D numpy ndarray of H magnitude
        Kmag (ndarray):
            1D numpy ndarray of K magnitude
        BV (ndarray):
            1D numpy ndarray of B-V Johnson magnitude
        MV (ndarray):
            1D numpy ndarray of absolute V magnitude
        BC (ndarray):
            1D numpy ndarray of bolometric correction
        L (ndarray):
            1D numpy ndarray of stellar luminosity in Solar luminosities
        Binary_Cut (ndarray):
            1D numpy ndarray of booleans where True is a star with a companion 
            closer than 10 arcsec
        dist (Quantity):
            1D numpy ndarray of distance to star (default units of parsecs)
        parx (Quantity):
            1D numpy ndarray of parallax (default units of milliarcseconds)
        coords (SkyCoord):
            numpy ndarray of astropy SkyCoord objects containing right ascension,
            declination, and distance to star (default units of degree and parsecs)
        pmra (Quantity):
            1D numpy ndarray of proper motion in right ascension (default units of 
            milliarcseconds/year)
        pmdec (Quantity):
            1D numpy ndarray of proper motion in declination (default units of 
            milliarcseconds/year)
        rv (Quantity):
            1D numpy ndarray of radial velocity (default units of km/s)
        maxintTime (Quantity):
            1D numpy ndarray containing maximum integration time (units of time)
        comp0 (ndarray):
            1D numpy ndarray containing completeness value for each target star
        MsEst (ndarray):
            1D numpy ndarray containing 'approximate' stellar mass in M_sun
        MsTrue (ndarray):
            1D numpy ndarray containing 'true' stellar mass in M_sun
        nStars (int):
            number of target stars
        minComp (float): 
            minimum completeness level for inclusion in target list
            
    
    """

    _modtype = 'TargetList'
    _outspec = {}

    def __init__(self, keepStarCatalog=False, minComp=0.1, **specs):
        """
        Initializes target list
        
        """

        #validate inputs
        assert isinstance(minComp,numbers.Number),\
                "minComp must be a number."
        assert isinstance(keepStarCatalog,bool),\
                "keepStarCatalog must be a boolean."
        self.minComp = float(minComp)

        
        # get desired module names (specific or prototype) and instantiate objects
        self.StarCatalog = get_module(specs['modules']['StarCatalog'],'StarCatalog')(**specs)
        self.ZodiacalLight = get_module(specs['modules']['ZodiacalLight'],'ZodiacalLight')(**specs)
        self.OpticalSystem = get_module(specs['modules']['OpticalSystem'],'OpticalSystem')(**specs)
        self.PostProcessing = get_module(specs['modules']['PostProcessing'],'PostProcessing')(**specs)
        self.Completeness = get_module(specs['modules']['Completeness'],'Completeness')(**specs)
        
        # bring inherited class objects to top level of Simulated Universe
        Comp = self.Completeness
        self.PlanetPopulation = Comp.PlanetPopulation
        self.PlanetPhysicalModel = Comp.PlanetPhysicalModel
        self.BackgroundSources = self.PostProcessing.BackgroundSources
        
        # list of possible Star Catalog attributes
        self.catalog_atts = ['Name', 'Spec', 'parx', 'Umag', 'Bmag', 'Vmag', 'Rmag', 
                'Imag', 'Jmag', 'Hmag', 'Kmag', 'dist', 'BV', 'MV', 'BC', 'L', 
                'coords', 'pmra', 'pmdec', 'rv', 'Binary_Cut']
        
        # now populate and filter the list
        self.populate_target_list(**specs)
        self.filter_target_list(**specs)
        
        # generate any completeness update data needed
        self.Completeness.gen_update(self)
        
        # have target list, no need for catalog now
        if not keepStarCatalog:
            del self.StarCatalog
        
        # populate outspec
        self._outspec['nStars'] = self.nStars
        self._outspec['keepStarCatalog'] = keepStarCatalog
        self._outspec['minComp'] = self.minComp

    def __str__(self):
        """String representation of the Target List object
        
        When the command 'print' is used on the Target List object, this method
        will return the values contained in the object"""
        
        for att in self.__dict__.keys():
            print '%s: %r' % (att, getattr(self, att))
        
        return 'Target List class object attributes'

    def populate_target_list(self, **specs):
        """ 
        This function is actually responsible for populating values from the star catalog
        (or any other source) into the target list attributes.
        
        The prototype implementation does the following:
        
        Copy directly from star catalog and remove stars with any NaN attributes
        Calculate completeness and max integration time, and generates stellar masses.
        
        """
        
        SC = self.StarCatalog
        Comp = self.Completeness
        OS = self.OpticalSystem
        ZL = self.ZodiacalLight
        
        # bring Star Catalog values to top level of Target List
        for att in self.catalog_atts:
            if type(getattr(SC, att)) == np.ma.core.MaskedArray:
                setattr(self, att, getattr(SC, att).filled(fill_value=float('nan')))
            else:
                setattr(self, att, getattr(SC, att))
        
        # number of target stars
        self.nStars = len(self.Name);
        # filter out nan attribute values from Star Catalog
        self.nan_filter()
        # populate completeness values
        self.comp0 = Comp.target_completeness(self)
        # populate maximum integration time
        self.maxintTime = OS.calc_maxintTime(self)
        # calculate 'true' and 'approximate' stellar masses
        self.stellar_mass()
        
        # include new attributes to the target list catalog attributes
        self.catalog_atts.append('comp0')
        self.catalog_atts.append('maxintTime')

    def filter_target_list(self,**specs):
        """ 
        This function is responsible for filtering by any required metrics.
        
        The prototype implementation does the following:
        
        binary stars are removed
        maximum integration time is calculated
        Filters applied to star catalog data:
            *systems with planets inside the IWA removed
            *systems where maximum delta mag is not in allowable orbital range 
            removed
            *systems where integration time is longer than maximum time removed
            *systems not meeting the completeness threshold removed
        
        Additional filters can be provided in specific TargetList implementations.
        """
        
        # filter out binary stars
        self.binary_filter()
        # filter out systems with planets within the IWA
        self.outside_IWA_filter()
        # filter out systems where maximum delta mag is not in allowable orbital range
        self.max_dmag_filter()
        # filter out systems where integration time is longer than maximum time
        self.int_cutoff_filter()
        # filter out systems which do not reach the completeness threshold
        self.completeness_filter()

    def nan_filter(self):
        """Populates Target List and filters out values which are nan
        
        """
        
        # filter out nan values in numerical attributes
        for att in self.catalog_atts:
            if getattr(self, att).shape[0] == 0:
                pass
            elif type(getattr(self, att)[0]) == str:
                # FIXME: intent here unclear: 
                #   note float('nan') is an IEEE NaN, getattr(.) is a str, and != on NaNs is special
                i = np.where(getattr(self, att) != float('nan'))[0]
                self.revise_lists(i)
            # exclude non-numerical types
            elif type(getattr(self, att)[0]) not in (np.unicode_, np.string_, np.bool_):
                if att == 'coords':
                    i1 = np.where(~np.isnan(self.coords.ra.to('deg').value))[0]
                    i2 = np.where(~np.isnan(self.coords.dec.to('deg').value))[0]
                    i = np.intersect1d(i1,i2)
                else:
                    i = np.where(~np.isnan(getattr(self, att)))[0]
                self.revise_lists(i)

    def binary_filter(self):
        """Removes stars which have attribute Binary_Cut == True
        
        """
        
        i = np.where(self.Binary_Cut == False)[0]
        self.revise_lists(i)

    def life_expectancy_filter(self):
        """Removes stars from Target List which have BV < 0.3
        
        """
        
        i = np.where(self.BV > 0.3)[0]
        self.revise_lists(i)

    def main_sequence_filter(self):
        """Removes stars from Target List which are not main sequence
        
        """
        
        # indices from Target List to keep
        i1 = np.where((self.BV < 0.74) & (self.MV < 6*self.BV+1.8))[0]
        i2 = np.where((self.BV >= 0.74) & (self.BV < 1.37) & (self.MV < 4.3*self.BV+3.05))[0]
        i3 = np.where((self.BV >= 1.37) & (self.MV < 18*self.BV-15.7))[0]
        i4 = np.where((self.BV < 0.87) & (self.MV > -8*(self.BV-1.35)**2+7.01))[0]
        i5 = np.where((self.BV >= 0.87) & (self.BV < 1.45) & (self.MV < 5*self.BV+0.81))[0]
        i6 = np.where((self.BV >= 1.45) & (self.MV > 18*self.BV-18.04))[0]
        ia = np.append(np.append(i1, i2), i3)
        ib = np.append(np.append(i4, i5), i6)
        i = np.intersect1d(np.unique(ia),np.unique(ib))
        self.revise_lists(i)

    def fgk_filter(self):
        """Includes only F, G, K spectral type stars in Target List
        
        """
        
        iF = np.where(np.core.defchararray.startswith(self.Spec, 'F'))[0]
        iG = np.where(np.core.defchararray.startswith(self.Spec, 'G'))[0]
        iK = np.where(np.core.defchararray.startswith(self.Spec, 'K'))[0]
        i = np.append(np.append(iF, iG), iK)
        i = np.unique(i)
        self.revise_lists(i)

    def vis_mag_filter(self, Vmagcrit):
        """Includes stars which are below the maximum apparent visual magnitude
        
        Args:
            Vmagcrit (float):
                maximum apparent visual magnitude
        
        """
        
        i = np.where(self.Vmag < Vmagcrit)[0]
        self.revise_lists(i)

    def outside_IWA_filter(self):
        """Includes stars with planets with orbits outside of the IWA 
        
        """
        
        OS = self.OpticalSystem
        PPop = self.PlanetPopulation
        
        s = np.tan(OS.IWA)*self.dist
        L = np.sqrt(self.L) if PPop.scaleOrbits else 1. # stellar luminosity in Solar luminosities
        i = np.where(s < L*np.max(PPop.rrange))[0]
        self.revise_lists(i)

    def int_cutoff_filter(self):
        """Includes stars if calculated integration time is less than cutoff
        
        """
        
        i = np.where(self.maxintTime <= self.OpticalSystem.intCutoff)[0]
        self.revise_lists(i)

    def max_dmag_filter(self):
        """Includes stars if maximum delta mag is in the allowed orbital range
        
        """
        
        OS = self.OpticalSystem
        PPop = self.PlanetPopulation
        PPMod = self.PlanetPhysicalModel
        
        # s and beta arrays
        s = np.tan(OS.IWA)*self.dist
        if PPop.scaleOrbits:
            s /= np.sqrt(self.L)
        beta = np.array([1.10472881476178]*len(s))*u.rad
        
        # fix out of range values
        below = np.where(s < np.min(PPop.rrange)*np.sin(beta))[0]
        above = np.where(s > np.max(PPop.rrange)*np.sin(beta))[0]
        s[below] = np.sin(beta[below])*np.min(PPop.rrange)
        beta[above] = np.arcsin(s[above]/np.max(PPop.rrange))
        
        # calculate delta mag
        p = np.max(PPop.prange)
        Rp = np.max(PPop.Rrange)
        d = s/np.sin(beta)
        Phi = PPMod.calc_Phi(beta)
        i = np.where(deltaMag(p,Rp,d,Phi) < OS.dMagLim)[0]
        self.revise_lists(i)

    def completeness_filter(self):
        """Includes stars if completeness is larger than the minimum value
        
        """
        
        i = np.where(self.comp0 > self.minComp)[0]
        self.revise_lists(i)

    def revise_lists(self, ind):
        """Replaces Target List catalog attributes with filtered values, 
        and updates the number of target stars.
        
        Args:
            ind (ndarray):
                1D numpy ndarray of indices to keep
        
        """
        
        for att in self.catalog_atts:
            if att == 'coords':
                ra = self.coords.ra[ind].to('deg')
                dec = self.coords.dec[ind].to('deg')
                self.coords = SkyCoord(ra, dec, self.dist.to('pc'))
            else:
                if getattr(self, att).size != 0:
                    setattr(self, att, getattr(self, att)[ind])
        
        self.nStars = len(ind)
        assert self.nStars, "Target list is empty: nStars = %r"%self.nStars

    def stellar_mass(self):
        """Populates target list with 'true' and 'approximate' stellar masses
        
        This method calculates stellar mass via the formula relating absolute V
        magnitude and stellar mass.  The values are in terms of M_sun.
        
        """
        
        # 'approximate' stellar mass
        self.MsEst = (10.**(0.002456*self.MV**2 - 0.09711*self.MV + 0.4365))
        # normally distributed 'error'
        err = (np.random.random(len(self.MV))*2. - 1.)*0.07
        self.MsTrue = (1. + err)*self.MsEst
        
        # if additional filters are desired, need self.catalog_atts fully populated
        self.catalog_atts.append('MsEst')
        self.catalog_atts.append('MsTrue')

    def starMag(self, sInds, lam):
        """Calculates star visual magnitudes with B-V color using empirical fit 
        to data from Pecaut and Mamajek (2013, Appendix C).
        The expression for flux is accurate to about 7%, in the range of validity 
        400 nm < λ < 1000 nm (Traub et al. 2016).
        
        Args:
            sInds (integer ndarray):
                Indices of the stars of interest
            lam (astropy Quantity):
                Wavelength in units of nm
        
        Returns:
            mV (float ndarray):
                Star visual magnitudes with B-V color
        
        """
        
        # check type of sInds
        sInds = np.array(sInds)
        if not sInds.shape:
            sInds = np.array([sInds])
        
        Vmag = self.Vmag[sInds]
        BV = self.BV[sInds]
        
        lam_um = lam.to('um').value
        if lam_um < .550:
            b = 2.20
        else:
            b = 1.54
        mV = Vmag + b*BV*(1/lam_um - 1.818)
        
        return mV
