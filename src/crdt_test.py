from py3crdt.sequence import Sequence
import uuid
from datetime import datetime

# Create a Sequence
seq1 = Sequence(uuid.uuid4())

# Create another Sequence
seq2 = Sequence(uuid.uuid4())

# Create another Sequence
seq3 = Sequence(uuid.uuid4())

# Add elements to seq1
id1a = [1, 0, 0]
seq1.add("z", id1a)
id1b = [2, 0, 0]
seq1.add("a", id1b)

# Add elements to seq2
id2c = [0, 1, 0]
seq2.add("aa", id2c)
id2b = [1, 2, 0]
seq2.add("aa", id2b)
id2d = [2, 2, 0]
seq2.add("aa", id2d)

seq1.display()
print("------")
seq2.display()
