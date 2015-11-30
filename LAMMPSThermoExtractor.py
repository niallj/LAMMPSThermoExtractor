class LAMMPSThermoData:
  def __init__(self, thermolines):
    import numpy as np

    self.names = thermolines.pop(0).split()
    self.values = np.fromstring("".join(thermolines), sep="\n")
    rows = len(thermolines)
    cols = len(self.names)
    self.values = self.values.reshape((rows, cols))

class LAMMPSLogFile:
  #these are the start and end points of the thermodynamic data block in the log
  thermo_block_begin = "Memory usage per processor"
  thermo_block_end = "Loop time"

  thermodata_blocks = []

  def __init__(self, filename):
    self.filename = filename

  def parse(self):
    def fragment_check(frag,line):
      return (line[0:len(frag)] == frag)

    with open(self.filename) as f:
      inside_thermo_block = False
      current_thermo_block = []
      for line in f:
        if inside_thermo_block:
          if fragment_check(self.thermo_block_end, line):
            inside_thermo_block = False
            ###TODO: Parse timing information
            self.thermodata_blocks.append(LAMMPSThermoData(current_thermo_block))
            current_thermo_block.clear()
          else:
            current_thermo_block.append(line)
        else:
          if fragment_check(self.thermo_block_begin, line):
            inside_thermo_block = True

  def loop_blocks(self):
    for b in self.thermodata_blocks:
      yield b.names, b.values

if __name__ == "__main__":
  import argparse
  import numpy as np
  parser = argparse.ArgumentParser()
  parser.add_argument("filename", type=str, help="LAMMPS log file to parse")
  parser.add_argument("--filepattern", type=str, default="thermo{i}.dat",
      help="Pattern for the output filenames. {i} represents the block number.")
  parser.add_argument("--onlyfields", type=str, nargs="*", help="Include only "
      "the given fields in the output files.")
  args = parser.parse_args()

  l = LAMMPSLogFile(args.filename)
  l.parse()

  for i,b in enumerate(l.loop_blocks()):
    n = b[0]
    filename = args.filepattern.format(i=i)
    if args.onlyfields:
      columns = [i for i,name in enumerate(n) if name in args.onlyfields]
      if len(columns) == 0:
        continue
      else:
        v = b[1][:, columns]
        headerline = " ".join(args.onlyfields)
        np.savetxt(filename, v, header=headerline)
    else:
      v = b[1]
      headerline = " ".join(n)
      np.savetxt(filename, v, header=headerline)
