from py3crdt.gset import GSet
import json

gset1 = GSet(id=1)
gset2 = GSet(id=2)
gset1.add(json.dumps({"data": 123425346}))
gset1.add(json.dumps({"data": 234525}))
gset1.add(json.dumps({"data": 124234}))
gset1.add(json.dumps({"data": 33}))
gset1.add(json.dumps({"data": 4654564644}))
gset1.display()
# ['a', 'b']   ----- Output
gset2.add(json.dumps({"data": 55}))
gset2.add(json.dumps({"data": 4654564644}))
gset2.add(json.dumps({"data": 123425346}))
gset2.add(json.dumps({"data": 234525}))
gset2.add(json.dumps({"data": 22}))
gset2.add(json.dumps({"data": 124234}))
gset2.display()
# ['b', 'c']   ----- Output
gset1.merge(gset2)
gset1.display()
# ['a', 'b', 'c']   ----- Output
gset2.merge(gset1)
gset2.display()
# ['a', 'b', 'c']   ----- Output
