class LAMMPSThermoData:
  time = None
  def __init__(self, thermolines, timing_data=None):
    import numpy as np
    from scipy.stats import sem

    self.names = thermolines.pop(0).split()
    self.values = np.fromstring("".join(thermolines), sep="\n")
    rows = len(thermolines)
    cols = len(self.names)
    self.values = self.values.reshape((rows, cols))

    if timing_data:
      self.time, self.procs, self.steps, self.atoms = list(map(float, timing_data))

    self.mean = np.mean(self.values, axis=0)
    self.stddev = np.std(self.values, axis=0)
    self.stderr = sem(self.values, axis=0)

  def timing_string(self):
    if hasattr(self, "time"):
      output = "{steps} steps in {time} seconds.\n".format(
          steps=int(self.steps), time=self.time)
      output += "{s_per_step:e} seconds per step (~{steps_per_day:.2e} steps per day)\n".format(
          s_per_step=self.time/self.steps, steps_per_day=self.steps/self.time*86400)
      return output
    else:
      return "No timing data available."

class LAMMPSLogFile:
  #these are the start and end points of the thermodynamic data block in the log
  thermo_block_begin = "Memory usage per processor"
  thermo_block_end = "Loop time"
  timing_regex = "Loop time of ([0-9.]+) on ([0-9]+) procs(?: \(.+\))? for ([0-9]+) steps with ([0-9]+) atoms"

  thermodata_blocks = []

  def __init__(self, filename):
    self.filename = filename

  def parse(self):
    import re #needed to extract timing information
    def fragment_check(frag,line):
      return (line[0:len(frag)] == frag)

    with open(self.filename) as f:
      inside_thermo_block = False
      current_thermo_block = []
      for line in f:
        if inside_thermo_block:
          if fragment_check(self.thermo_block_end, line):
            inside_thermo_block = False
            regex = re.compile(self.timing_regex)
            m = regex.match(line)
            if not m:
              print("Error! Couldn't perform the regex match on the loop time information. The offending line was:")
              print(line)
              self.thermodata_blocks.append(LAMMPSThermoData(current_thermo_block))
            else:
              time, procs, steps, atoms = m.group(1, 2, 3, 4)
              self.thermodata_blocks.append(LAMMPSThermoData(current_thermo_block, (time, procs, steps, atoms)))
            current_thermo_block.clear()
          else:
            current_thermo_block.append(line)
        else:
          if fragment_check(self.thermo_block_begin, line):
            inside_thermo_block = True

  def loop_blocks(self):
    for b in self.thermodata_blocks:
      yield b

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

  no_stats = ["Time", "Step"]

  for i,b in enumerate(l.loop_blocks()):
    n = b.names
    filename = args.filepattern.format(i=i)
    statsline = "{:^20} {:^20} {:^20} {:^20}\n".format("Quantity", "Mean", "Std Dev", "Std Err")
    statsline += "-"*83+"\n"
    if args.onlyfields:
      columns = [i for i,name in enumerate(n) if name in args.onlyfields]
      if len(columns) == 0:
        continue
      else:
        for c in columns:
          if n[c] in no_stats:
            continue
          statsline += "{:^20} {:^20} {:^20} {:^20}\n".format(n[c], b.mean[c], b.stddev[c], b.stderr[c])
        column_list = " ".join(args.onlyfields)
        v = b.values[:, columns]
    else:
      for c, name in enumerate(n):
        if name in no_stats:
          continue
        statsline += "{:^20} {:^20} {:^20} {:^20}\n".format(name, b.mean[c], b.stddev[c], b.stderr[c])
      v = b.values
      column_list = " ".join(n)

    headerline = "{:^80}\n{:^80}\n\n".format("Columns in file:", column_list)
    headerline += "{:^80}\n{}\n".format("Statistics", "-"*83)
    headerline += statsline
    headerline += "-"*83+"\n\n"
    headerline += "{:^80}\n{}\n{}\n{}\n\n".format("Timing Information", "-"*83, b.timing_string()[:-1], "-"*83)
    headerline += column_list
    np.savetxt(filename, v, header=headerline)

