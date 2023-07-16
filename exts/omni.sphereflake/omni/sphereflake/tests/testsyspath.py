import sys

def write_out_syspath(fname: str = 'd:/nv/ov/syspath.txt', indent=False) -> None:
    # Write out the python syspath to a file 
    # Indent should be True if to be used for the settings.json python.analsys.extraPaths setting
    pplist = sys.path
    with open(fname, 'w') as f:
        for line in pplist:
            nline = line.replace("\\", "/")
            if indent:
              nnline = f"        \"{nline}\",\n"
            else:
              nnline = f"\"{nline}\",\n"
            f.write(nnline)


def read_in_syspath(fname: str = 'd:/nv/ov/syspath.txt') -> None:
    # Read in the python path from a file 
    with open(fname, 'r') as f:
        for line in f:
            nline = line.replace(',', '')
            nline = nline.replace('"', '')
            nline = nline.replace('"', '')
            nline = nline.replace('\n', '')
            nline = nline.replace(' ', '')
            sys.path.append(nline)
            
            
write_out_syspath("syspath-before.txt")

read_in_syspath("syspath-before.txt")

write_out_syspath("syspath-after.txt")
