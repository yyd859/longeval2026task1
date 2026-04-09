from ir_datasets_longeval import load

# load an official version of the LongEval dataset.
dataset = load("longeval-sci-2026/snapshot-3")

# load a local copy of a LongEval dataset.
# E.g., so that you can easily run your approach on modified data.
dataset = load("<PATH-TO-A-DIRECTORY-ON-YOUR-MACHINE>")

# From now on, you can use dataset as any ir_dataset