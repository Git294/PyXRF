## PyXRF

PyXRF is a python-based sophisticated fluorescence analysis package for
fitting and visualizing X-ray fluorescence data. This package contains a
high-level fitting engine, comprehensive command-line/GUI design, rigorous
physics calculation and a powerful visualization interface. The theoretical
part of PyXRF is based on MAPS, developed by Stefan Vogt at APS. PyXRF offers
some of the unique features as follows.
- Automatic elements finding: Users do not need to spend extra time selecting
  elements manually.
- Forward calculation: Users can observe the spectrum from forward calculation
  at real time while adjusting input parameters. This will help users perform
  sensitivity analysis, and find an appropriate initial guess for fitting.
- Construct your own fitting algorithm: An advanced mode was created for
  advanced users to construct their own fitting strategies with a full
  control of each fitting parameter.
- Batch mode: Users can easily perform quick fitting of multiple fluorescence
  datasets or XANES datasets.
- Interface with NSLS-II database: A specific I/O interface was designed to
   obtain data directly from BNL/NSLS-II experimental database.

## Installation from Conda
PyXRF works for both python 2.7 and 3.5 in Linux/Mac system. For windows, we only support 3.5 for windows 10(64 bit).

### Linux/Mac
First you need to install [conda] (http://continuum.io/downloads). We suggest
anaconda because it is a complete installation of the entire scientific python
stack, but is ~400 MB.  For advanced users, consider downloading [miniconda]
(http://conda.pydata.org/miniconda.html) because it is a smaller download (~20 MB).

Then create a conda environment(say pyxrf_test) with python3.5.
```
$ conda create -n pyxrf_test python=3.5
```
Then go to the environment named pyxrf_test
```
$ source activate pyxrf_test
```
At the same environment, install pyxrf by simply typing
```
$ conda install pyxrf pyqt=4.11 enaml=0.9.8 -c lightsource2-tag
```

### Windows
Install anaconda windows version from (http://continuum.io/downloads).
Then you should Anaconda Prompt installed in your computer. Double click Anaconda Prompt, and type the following lines to finish the installation.

Then create a conda environment(say pyxrf_test) with python3.5.
```
$ conda create -n pyxrf_test python=3.5
```
Then go to the environment named pyxrf_test
```
$ activate pyxrf_test
```
At the same environment, install pyxrf by simply typing
```
$ conda install pyxrf xraylib pyqt=4.11 -c lightsource2-tag -c conda-forge
```

### Run
```
$ pyxrf
```

#### Update
```
$ conda update pyxrf -c lightsource2-tag
```

#### Reminder
Every time you open a new terminal, make sure to go to pyxrf_test environment first, then launch the software. For linux and mac system, type
```
$ source activate pyxrf_test
```
for windows,
```
activate pyxrf_test        
```
then lanch pyxrf by typing
```
$ pyxrf
```

To leave this environment, at Linux and Mac system just type
```
$ source deactivate
```
and for Windows, type
```
deactivate          
```

## Documentation

### h5 file for PyXRF
Please download a standard h5 file from the link
https://drive.google.com/file/d/0B45Mm22EF9TNQzFkSW0xa01mbkE/view
This h5 file mainly contains spectrum from 3 detectors, positions of x,y motors and scalers for normalization. Please create h5 file with a similar structure in order to use PyXRF.

For test purposes, a parameter file (https://drive.google.com/file/d/0B45Mm22EF9TNYW11OXozRXVic1E/view) is also provided for users to do fitting for this standard h5 file. However, you should never create parameter file manually. Parameter file can be easily created during the step of automatic peak finding.

### spec file for PyXRF
Users can transfer spec file to hdf file that pyxrf can take. Please see examples at https://github.com/NSLS-II/PyXRF/blob/master/examples/specfile_to_hdf.ipynb

### youtube tutorial
The latest youtube tutorial of pyxrf version 0.0.4 is at https://www.youtube.com/watch?v=2nFLccehaHI

You may also refer to http://nbviewer.ipython.org/gist/licode/06654b079fd617aaaeca

More documentation will be ready soon!


## Notes

The core fitting functions are a part of the [scikit-beam]
(https://github.com/scikit-beam/scikit-beam) data analysis library for x-ray data analysis.
The design philosophy is to separate fitting and gui, so it is easy to maintain.
For more questions, please submit issues through github, or contact Li at lili@bnl.gov.
