#!/usr/bin/env python
import subprocess
import time
from sipprCommon.sippingmethods import *
from sipprCommon.objectprep import Objectprep
from accessoryFunctions.accessoryFunctions import *
from accessoryFunctions.metadataprinter import *

__author__ = 'adamkoziol'


class GeneSippr(object):

    def runner(self):
        """
        Run the necessary methods in the correct order
        """
        printtime('Starting {} analysis pipeline'.format(self.analysistype), self.starttime)
        # Create the objects to be used in the analyses
        objects = Objectprep(self)
        objects.objectprep()
        self.runmetadata = objects.samples
        # Run the analyses
        Sippr(self, self.cutoff)
        # Create the reports
        self.reporter()
        # Print the metadata
        printer = MetadataPrinter(self)
        printer.printmetadata()

    def reporter(self):
        """
        Creates a report of the results
        """
        # Create the path in which the reports are stored
        make_path(self.reportpath)
        header = 'Strain,Gene,PercentIdentity,FoldCoverage\n'
        data = ''
        with open('{}/{}.csv'.format(self.reportpath, self.analysistype), 'w') as report:
            for sample in self.runmetadata.samples:
                data += sample.name + ','
                if sample[self.analysistype].results:
                    multiple = False
                    for name, identity in sample[self.analysistype].results.items():
                        if not multiple:
                            data += '{},{},{}\n'.format(name, identity, sample[self.analysistype].avgdepth[name])
                        else:
                            data += ',{},{},{}\n'.format(name, identity, sample[self.analysistype].avgdepth[name])
                        multiple = True
                else:
                    data += '\n'
            report.write(header)
            report.write(data)

    def __init__(self, args, pipelinecommit, startingtime, scriptpath):
        """
        :param args: command line arguments
        :param pipelinecommit: pipeline commit or version
        :param startingtime: time the script was started
        :param scriptpath: home path of the script
        """
        import multiprocessing
        # Initialise variables
        self.commit = str(pipelinecommit)
        self.starttime = startingtime
        self.homepath = scriptpath
        # Define variables based on supplied arguments
        self.path = os.path.join(args.path, '')
        assert os.path.isdir(self.path), u'Supplied path is not a valid directory {0!r:s}'.format(self.path)
        self.sequencepath = os.path.join(args.sequencepath, '')
        assert os.path.isdir(self.sequencepath), u'Sequence path  is not a valid directory {0!r:s}' \
            .format(self.sequencepath)
        self.targetpath = os.path.join(args.targetpath, '')
        self.reportpath = os.path.join(self.path, 'reports')
        assert os.path.isdir(self.targetpath), u'Target path is not a valid directory {0!r:s}' \
            .format(self.targetpath)
        self.bcltofastq = args.bcl2fastq
        self.miseqpath = args.miseqpath
        self.miseqfolder = args.miseqfolder
        self.fastqdestination = args.destinationfastq
        self.forwardlength = args.readlengthforward
        self.reverselength = args.readlengthreverse
        self.numreads = 2 if self.reverselength != 0 else 1
        self.customsamplesheet = args.customsamplesheet
        # Set the custom cutoff value
        self.cutoff = args.customcutoffs
        self.copy = args.copy
        self.runmetadata = MetadataObject()
        # Use the argument for the number of threads to use, or default to the number of cpus in the system
        self.cpus = int(args.numthreads if args.numthreads else multiprocessing.cpu_count())
        try:
            self.threads = int(self.cpus / len(self.runmetadata.samples)) if self.cpus / len(self.runmetadata.samples) \
                                                                             > 1 else 1
        except TypeError:
            self.threads = self.cpus
        self.taxonomy = {'Escherichia': 'coli', 'Listeria': 'monocytogenes', 'Salmonella': 'enterica'}
        self.analysistype = 'genesippr'
        self.pipeline = False
        # Run the analyses
        self.runner()

if __name__ == '__main__':
    # Argument parser for user-inputted values, and a nifty help menu
    from argparse import ArgumentParser
    # Get the current commit of the pipeline from git
    # Extract the path of the current script from the full path + file name
    homepath = os.path.split(os.path.abspath(__file__))[0]
    # Find the commit of the script by running a command to change to the directory containing the script and run
    # a git command to return the short version of the commit hash
    commit = subprocess.Popen('cd {} && git rev-parse --short HEAD'.format(homepath),
                              shell=True, stdout=subprocess.PIPE).communicate()[0].rstrip()
    # Parser for arguments
    parser = ArgumentParser(description='Perform modelling of parameters for GeneSipping')
    parser.add_argument('path',
                        help='Specify input directory')
    parser.add_argument('-s', '--sequencepath',
                        required=True,
                        help='Path of .fastq(.gz) files to process.')
    parser.add_argument('-t', '--targetpath',
                        required=True,
                        help='Path of target files to process.')
    parser.add_argument('-n', '--numthreads',
                        help='Number of threads. Default is the number of cores in the system')
    parser.add_argument('-b', '--bcl2fastq',
                        action='store_true',
                        help='Optionally run bcl2fastq on an in-progress Illumina MiSeq run. Must include:'
                             'miseqpath, and miseqfolder arguments, and optionally readlengthforward, '
                             'readlengthreverse, and projectName arguments.')
    parser.add_argument('-m', '--miseqpath',
                        help='Path of the folder containing MiSeq run data folder')
    parser.add_argument('-f', '--miseqfolder',
                        help='Name of the folder containing MiSeq run data')
    parser.add_argument('-d', '--destinationfastq',
                        help='Optional folder path to store .fastq files created using the fastqCreation module. '
                             'Defaults to path/miseqfolder')
    parser.add_argument('-r1', '--readlengthforward',
                        default='full',
                        help='Length of forward reads to use. Can specify "full" to take the full length of '
                             'forward reads specified on the SampleSheet')
    parser.add_argument('-r2', '--readlengthreverse',
                        default='full',
                        help='Length of reverse reads to use. Can specify "full" to take the full length of '
                             'reverse reads specified on the SampleSheet')
    parser.add_argument('-c', '--customsamplesheet',
                        help='Path of folder containing a custom sample sheet (still must be named "SampleSheet.csv")')
    parser.add_argument('-P', '--projectName',
                        help='A name for the analyses. If nothing is provided, then the "Sample_Project" field '
                             'in the provided sample sheet will be used. Please note that bcl2fastq creates '
                             'subfolders using the project name, so if multiple names are provided, the results '
                             'will be split as into multiple projects')
    parser.add_argument('-D', '--detailedReports',
                        action='store_true',
                        help='Provide detailed reports with percent identity and depth of coverage values '
                             'rather than just "+" for positive results')
    parser.add_argument('-u', '--customcutoffs',
                        default=0.8,
                        help='Custom cutoff values')
    parser.add_argument('-C', '--copy',
                        action='store_true',
                        help='Normally, the program will create symbolic links of the files into the sequence path, '
                             'however, the are occasions when it is necessary to copy the files instead')
    # Get the arguments into an object
    arguments = parser.parse_args()

    # Define the start time
    start = time.time()

    # Run the script
    GeneSippr(arguments, commit, start, homepath)

    # Print a bold, green exit statement
    print('\033[92m' + '\033[1m' + "\nElapsed Time: %0.2f seconds" % (time.time() - start) + '\033[0m')
