"""
A python module for plotting and manipulating seismic data and headers,
kirchhoff migration and more. Contains the following functions

wiggle                  : Seismic wiggle plot
imageseis               : Interactive seismic image

sorthdr                 : sort seismic header
sortdata                : sort seismic data
selectCMP               : select a CMP gather with respect to its midpoint position
analysefold             : Positions of gathers and their folds
plothdr                 : Plots header data
semblanceWiggle         : Interactive semblance plot for velocity analysis
apply_nmo               : Applies nmo correction
nmo_v                   : Applies nmo to single CMP gather for constant velocity
nmo_vlog                : Applied nmo to single CMP gather for a 1D time-velocity log
nmo_stack               : Generates a stacked zero-offset section
stackplot               : Stacks all traces in a gather and plots the stacked trace
generatevmodel2         : Generates a 2D velocity model
time2depth_trace        : time-to-depth conversion for a single trace in time domain
time2depth_section      : time-to-depth conversion for a seismic section in time domain
agc                     : applies automatic gain control for a given dataset.

(C) Nicolas Vinard and Musab al Hasani, 2020, v.2.0.0

- 29.07.2020 Rewritten ToolBox to class with wiggle, imageseis and print_beta functions
- 31.01.2020 added nth-percentile clipping
- 16.01.2020 Added clipping in wiggle function
- added agc functions
- Fixed semblanceWiggle sorting error



Many of the functions here were developed by CREWES and were originally written in MATLAB.
In the comments of every function we translated from CREWES we refer to its function name
and the CREWES Matlab library at www.crewes.org.
Other functions were translated from MATLAB to Python and originally written by Max Holicki
for the course "Geophyiscal methods for subsurface characterization" tought at TU Delft.

"""

import struct, sys
import numpy as np
import matplotlib
import copy
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import sys
from typing import Tuple
from tqdm import tnrange

##################################################
########## HEADER AND DATA MANIPULATION ##########
##################################################

class seismicToolBox(object):

    '''
    The seismicToolBox contains many functions for plotting Headers and Data and manipulating them.

    '''

    def __init__(self, segy):

        '''
        You can access the Data, Header (SH) and the STH from yor initiated seismicToolBox object.

        TODO: ADD ERRROR MESSAGE IF NOT TUPLE OF 3

        Example
        -------

        # First read in the segy data using segypy:

        dataset = segypy.readSegy("/path/to/shot.segy")

        # The create the seismicToolBox object
        seismic = seismicToolBox(dataset)

        # You can then access the Data, SH and STH in the following way
        seismic.Data
        seismic.SH
        seismic.STH

        '''
        self.Data = segy[0]
        self.SH = segy[1]
        self.STH = segy[2]
        self.dt = self.SH['dt']/1000000

    def print_beta(self):
        '''
        print_beta prints useful beta information such as the time step.
        '''

        print("time step in s: {}".format(self.dt))
        print("receiver sampling: {}".format(self.STH[4,1]-self.STH[4,0]))

    def wiggle(self, x=None, t=None, trace_interval=None, timesample_interval=None, timewindow=False,
               perc=100, skipt=1, lwidth=.5, gain=1, typeD='VA', color='red'):

        '''
        wiggle(=None, t=None, maxval=-1, skipt=1, lwidth=.5, gain=1, typeD='VA', color='red', perc=100)

        This function generates a wiggle plot of the seismic data. The traces are plotted on the x-coordinate
        and the timesamples are plotted along the y-coordinate.

        Optional parameters
        -------------------
        x: np.ndarray of shape Data.shape[1]
            x-coordinates to Plot
        t: np.ndarray of shape Data.shap[0]
            t-axis to plot
        trace_interval: list of length 2
            start and end point of traces to show: [start, end]
        timesample_interval: list of length 2
            start and end point of time samples to show: [start, end]
            If time is given in seconds set 'timewindow=True'
        timewindow: bool
            Default: False. Set to true if timesample_interval is given in seconds
        skipt: int
            Skip trace, skips every n-th trace
        ldwidth: float
            line width of the traces in the figure, increase or decreases the traces width
        typeD: string
            With or without filling positive amplitudes. Use type=None for no filling
        color: string
            Color of the traces
        perc: float
            nth parcintile to be clipped

        Returns
        -------
        Seismic wiggle plot

        Adapted from segypy (Thomas Mejer Hansen, https://github.com/cultpenguin/segypy/blob/master/segypy/segypy.py)
        '''

        if timewindow:
            starttime=timesample_interval[0]
            endtime=timesample_interval[1]

            timesample_interval[0] = int(timesample_interval[0]/self.dt)
            timesample_interval[1] = int(timesample_interval[1]/self.dt)
            print(timesample_interval)

        if trace_interval is not None:
            if len(trace_interval) != 2 or len(trace_interval) > 2:
                print("Error: trace_interval should be a list of two elements")
                sys.exit()
        if timesample_interval is not None:
            if len(timesample_interval) != 2 or len(timesample_interval) > 2:
                print("Error: trace_interval should be a list of two elements")
                sys.exit()


        # Make a copy of the original, so that it won't change the original one ouside the scope of the function
        Data = copy.copy(self.Data)

        if trace_interval is not None:
            Data = Data[:,int(trace_interval[0]):int(trace_interval[1])]
        if timesample_interval is not None:
            Data = Data[int(timesample_interval[0]):int(timesample_interval[1]), :]


        # calculate value of nth-percentile, when perc = 100, data won't be clipped.
        nth_percentile = np.abs(np.percentile(Data, perc))

        # clip data to the value of nth-percentile
        Data = np.clip(Data, a_min=-nth_percentile, a_max = nth_percentile)

        ns = Data.shape[0]
        ntraces = Data.shape[1]

        fig = plt.gca()
        ax = plt.gca()
        ntmax=1e+9 # used to be optinal

        if ntmax<ntraces:
            skipt=int(np.floor(ntraces/ntmax))
            if skipt<1:
                    skipt=1

        if x is not None:
            x=x
            ax.set_xlabel('Distance [m]')
        else:
            if trace_interval is not None:
                x = range(trace_interval[0], trace_interval[1])
            else:
                x = np.arange(0, ntraces)
            ax.set_xlabel('Trace number')

        if t is not None and timesample_interval is not None:
            t=t[timesample_interval[0]:timesample_interval[1]]
            yl='Time [s]'
        elif t is not None:
            t=t
            yl='Time [s]'
        elif timesample_interval is not None:
            t=range(timesample_interval[0], timesample_interval[1])
            yl='Sample number'
        else:
            t=np.arange(0, ns)
            yl='Sample number'

        dx = x[1]-x[0]

        Dmax = np.nanmax(Data)
        maxval = np.abs(Dmax)

        for i in range(0, ntraces, skipt):

            # use copy to avoid truncating the data
            trace = copy.copy(Data[:, i])
            trace = Data[:, i]
            trace[0] = 0
            trace[-1] = 0
            traceplt = x[i] + gain * skipt * dx * trace / maxval
            traceplt = np.clip(traceplt, a_min=x[i]-dx, a_max=(dx+x[i]))

            ax.plot(traceplt, t, color=color, linewidth=lwidth)

            offset = x[i]

            if typeD=='VA':
                for a in range(len(trace)):
                    if (trace[a] < 0):
                        trace[a] = 0
                ax.fill_betweenx(t, offset, traceplt, where=(traceplt>offset), interpolate='True', linewidth=0, color=color)
                ax.grid(False)

        ax.set_xlim([x[0]-1, x[-1]+1])
        ax.set_ylim([np.min(t), np.max(t)])
        ax.invert_yaxis()
        ax.set_ylabel(yl)



    def imageseis(self, x=None, t=None, trace_interval=None, timesample_interval=None, timewindow=False, gain=1, perc=100):
        """
        imageseis(x=None, t=None, trace_interval=None, timesample_interval=None, timewindow=False, gain=1, perc=100):

        This function generates a seismic image plot including interactive
        handles to apply a gain and a clip

        Optional parameters
        -------------------
        x: np.ndarray of shape Data.shape[1]
            x-coordinates to Plot
        t: np.ndarray of shape Data.shap[0]
            t-axis to plot
        trace_interval: list of length 2
            start and end point of traces to show: [start, end]
        timesample_interval: list of length 2
            start and end point of time samples to show: [start, end]
            If time is given in seconds set 'timewindow=True'
        timewindow: bool
            Default: False. Set to true if timesample_interval is given in seconds
        gain: float
            Apply simple gain
        perc: float
            nth parcintile to be clipped

        Returns
        -------
        Seismic image

        Adapted from segypy (Thomas Mejer Hansen, https://github.com/cultpenguin/segypy/blob/master/segypy/segypy.py)

        Musab and Nicolas added interactive gain and clip, 2019

        """

        if timewindow:
            starttime=timesample_interval[0]
            endtime=timesample_interval[1]

            timesample_interval[0] = int(timesample_interval[0]/self.dt)
            timesample_interval[1] = int(timesample_interval[1]/self.dt)
            print(timesample_interval)

        if trace_interval is not None:
            if len(trace_interval) != 2 or len(trace_interval) > 2:
                print("Error: trace_interval should be a list of two elements")
                sys.exit()
        if timesample_interval is not None:
            if len(timesample_interval) != 2 or len(timesample_interval) > 2:
                print("Error: timesample_interval should be a list of two elements")
                sys.exit()


        # Make a copy of the original, so that it won't change the original one ouside the scope of the function
        Data = copy.copy(self.Data)
        if trace_interval is not None:
            Data = Data[:,int(trace_interval[0]):int(trace_interval[1])]
        if timesample_interval is not None:
            Data = Data[int(timesample_interval[0]):int(timesample_interval[1]), :]

        # calculate value of nth-percentile, when perc = 100, data won't be clipped.
        nth_percentile = np.abs(np.percentile(Data, perc))

        # clip data to the value of nth-percintile
        Data = np.clip(Data, a_min=-nth_percentile, a_max = nth_percentile)

        ns, ntraces = Data.shape
        maxval = -1
        Dmax = np.max(Data)
        maxval = -1*maxval*Dmax

        #if t is None:
        #    t = np.arange(0, ns)
        #    tLabel = 'Sample number'
        #else:
        #    t = t
        #    tc = t
        #    tLabel = 'Time [s]'
        #    if len(t)!=ns:
        #        print('Error: time array not of same length as number of time samples in data \n Samples in data: {}, sample in input time array: {}'.format(ns, len(t)))
        #        sys.exit()

        if x is None:
            x = np.arange(0, ntraces) +1
            xLabel = 'Trace number'
        else:
            x = x
            xLabel = 'Distance [m]'
            if len(x)!=ntraces:
                print('Error: x array not of same length as number of trace samples in data \n Samples in data: {}, sample in input x array: {}'.format(ns, len(t)))
                sys.exit()
        if x is not None:
            x=x
            xLabel='Distance [m]'
        else:
            if trace_interval is not None:
                x = range(trace_interval[0], trace_interval[1])
            else:
                x = np.arange(0, ntraces)
            xLabel='Trace number'

        if t is not None and timesample_interval is not None:
            t=t[timesample_interval[0]:timesample_interval[1]]
            yl='Time [s]'
        elif t is not None:
            t=t
            yl='Time [s]'
        elif timesample_interval is not None:
            t=range(timesample_interval[0], timesample_interval[1])
            yl='Sample number'
        else:
            t=np.arange(0, ns)
            yl='Sample number'

        plt.subplots_adjust(left=0.25, bottom=0.3)
        img = plt.pcolormesh(x, t, Data*gain, vmin=-1*maxval, vmax=maxval, cmap='seismic')
        cb = plt.colorbar()
        plt.axis('normal')
        plt.xlabel(xLabel)
        plt.ylabel(yl)
        plt.gca().invert_yaxis()

        # Add interactice widgets
        # Defines position of the toolbars
        ax_cmax  = plt.axes([0.25, 0.15, 0.5, 0.03])
        ax_cmin = plt.axes([0.25, 0.1, 0.5, 0.03])
        ax_gain  = plt.axes([0.25, 0.05, 0.5, 0.03])

        s_cmax = Slider(ax_cmax, 'max clip ', 0, np.max(np.abs(Data)), valinit=np.max(np.abs(Data)))
        s_cmin = Slider(ax_cmin, 'min clip', -np.max(np.abs(Data)), 0, valinit=-np.max(np.abs(Data)))
        s_gain = Slider(ax_gain, 'gain', gain, 10*gain, valinit=gain)

        def update(val, s=None):
            _cmin = s_cmin.val/s_gain.val
            _cmax = s_cmax.val/s_gain.val
            img.set_clim([_cmin, _cmax])
            plt.draw()

        s_cmin.on_changed(update)
        s_cmax.on_changed(update)
        s_gain.on_changed(update)

        return img
