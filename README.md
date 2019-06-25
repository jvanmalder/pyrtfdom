Example instantiation:  

from pyrtfdom.dom import RTFDOM  
from pyrtfdom import elements  

domTree = RTFDOM()  
domTree.openFile('test.rtf')  
domTree.parse()  

domTree.printTree()  
