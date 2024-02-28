# from py3crdt.sequence import Sequence
# import uuid
# from datetime import datetime

# # Create a Sequence
# seq1 = Sequence(uuid.uuid4())

# # Create another Sequence
# seq2 = Sequence(uuid.uuid4())

# # Create another Sequence
# seq3 = Sequence(uuid.uuid4())

# # Add elements to seq1
# id1a = [1, 0, 0]
# seq1.add("z", id1a)
# id1b = [2, 0, 0]
# seq1.add("a", id1b)

# # Add elements to seq2
# id1a = [1, 0, 0]
# seq2.add("z", id1a)
# id1b = [2, 0, 0]
# seq2.add("a", id1b)


# seq1.display()
# print("------")
# seq2.display()

# print(hash(seq1))
# print(hash(seq2))

# rawr1 = set()
# rawr2 = set()
# for tx in seq1.elem_list:
#     rawr1.add((tx[0], sum(tx[1])))

# for tx in seq2.elem_list[::-1]:
#     rawr2.add((tx[0], sum(tx[1])))

# # Convert sets to frozensets before hashing
# frozen_rawr1 = frozenset(rawr1)
# frozen_rawr2 = frozenset(rawr2)

# print(seq1.elem_list)
# print(seq2.elem_list)

# print(hash(frozen_rawr1) == hash(frozen_rawr2))

# print(hash(""))

# ? Padding the number until it's a certain size
rand_num = 1
rand_num_len = len(str(1))
while int(rand_num_len) < 40:
    rand_num *= 10
    rand_num_len = len(str(rand_num))

rand_num = rand_num

# ? Our ranking function subtracts the random number from the node_id,
# ? then takes the mod of our block_index + some constant number
node_rank = []
node_ids = [-88, -55, -22, 12, 14, 55, 104, 557, 1024, 5678]
for node_id in node_ids:
    rank = (rand_num - int(node_id)) % (0 + 888)
    node_rank.append((rank, node_id))

node_rank.sort()

print(node_rank)
