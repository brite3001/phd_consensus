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
id1a = [1, 0, 0]
seq2.add("z", id1a)
id1b = [2, 0, 0]
seq2.add("a", id1b)
id1b = [3, 0, 0]
seq2.add("g", id1b)


seq1.display()
print("------")
seq2.display()

seq1.merge(seq2)

seq1.display()

print(seq1.query("z"))

# print(hash(seq1))
# print(hash(seq2))

# rawr1 = []
# rawr2 = []
# for tx in seq1.elem_list:
#     rawr1.append((tx[0], sum(tx[1])))

# for tx in seq2.elem_list:
#     rawr2.append((tx[0], sum(tx[1])))

# rawr1 = tuple(rawr1)
# print(hash(rawr1))

# Convert sets to frozensets before hashing
# frozen_rawr1 = frozenset(rawr1)
# frozen_rawr2 = frozenset(rawr2)

# print(seq1.elem_list)
# print(seq2.elem_list)

# print(hash(frozen_rawr1) == hash(frozen_rawr2))

# print(hash(""))
