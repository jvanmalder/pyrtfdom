Example instantiation:  

from pyrtfdom.dom import RTFDOM  

domTree = RTFDOM()  
domTree.openFile('test.rtf')  
domTree.parse()  

domTree.printTree()  
