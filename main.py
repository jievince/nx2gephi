import sys, getopt
import networkx as nx
from networkx.algorithms import community
import itertools
import matplotlib.pyplot as plt
sys.path.insert(0, '../')

from nebula.ngMeta.MetaClient import MetaClient
from nebula.ngStorage.StorageClient import StorageClient
from nebula.ngStorage.ngProcessor.ScanEdgeProcessor import ScanEdgeProcessor
from nebula.ngStorage.ngProcessor.ScanVertexProcessor import ScanVertexProcessor


def scanEdge(space, returnCols, allCols):
    scanEdgeResponseIter = storageClient.scanEdge(space, returnCols, allCols, 100, 0, sys.maxsize)
    scanEdgeResponse = scanEdgeResponseIter.next()
    if scanEdgeResponse is None:
        print('not ok')
    else:
        print('ok')
    processEdge(space, scanEdgeResponse)
    while scanEdgeResponseIter.hasNext():
        scanEdgeResponse = scanEdgeResponseIter.next()
        if scanEdgeResponse is None:
            print("Error occurs while scaning edge")
            break
        processEdge(space, scanEdgeResponse)

def scanVertex(space, returnCols, allCols):
    scanVertexResponseIter = storageClient.scanVertex(space, returnCols, allCols, 100, 0, sys.maxsize)
    scanVertexResponse = scanVertexResponseIter.next()
    if scanVertexResponse is None:
        print('not ok')
    else:
        print('ok')
    processVertex(space, scanVertexResponse)
    while scanVertexResponseIter.hasNext():
        scanVertexResponse = scanVertexResponseIter.next()
        if scanVertexResponse is None:
            print("Error occurs while scaning vertex")
            break
        processVertex(space, scanVertexResponse)

def processEdge(space, scanEdgeResponse):
    result = scanEdgeProcessor.process(space, scanEdgeResponse)
    # Get the corresponding rows by edgeName
    for edgeName, edgeRows in result.rows.items():
        #print('edgeName: ', edgeName)
        for row in edgeRows:
            srcId = row.defaultProperties[0].getValue()
            dstId = row.defaultProperties[2].getValue()
            #print('srcId: ', srcId, ' dstId: ', dstId)
            props = {}
            for prop in row.properties:
                propName = prop.getName()
                propValue = prop.getValue()
                props[propName] = propValue
            #print(props)
            G.add_edges_from([(srcId, dstId, props)])

def processVertex(space, scanVertexResponse):
    result = scanVertexProcessor.process(space, scanVertexResponse)
    if result is None:
        print('processVertex: result is None')
        return None
    for tagName, tagRows in result.rows.items():
        #print('tagName: ', tagName)
        for row in tagRows:
            vid = row.defaultProperties[0].getValue()
            #print('vid: ', vid)
            props = {}
            for prop in row.properties:
                propName = prop.getName()
                propValue = prop.getValue()
                props[propName] = propValue
            #print(props)
            G.add_nodes_from([(vid, props)])

def getReturnCols(space):
    tagItems = metaClient.getTags(space)
    vertexReturnCols = {}
    for tagItem in tagItems:
        tagName = tagItem.tag_name
        vertexReturnCols[tagName] = metaClient.getTagSchema(space, tagName).keys()
    edgeItems = metaClient.getEdges(space)
    edgeReturnCols = {}
    for edgeItem in edgeItems:
        edgeName = edgeItem.edge_name
        edgeReturnCols[edgeName] = metaClient.getEdgeSchema(space, edgeName).keys()

    return vertexReturnCols, edgeReturnCols


if __name__ == '__main__':
    metaClient = MetaClient([(sys.argv[1], sys.argv[2])])
    metaClient.connect()
    storageClient = StorageClient(metaClient)
    scanEdgeProcessor = ScanEdgeProcessor(metaClient)
    scanVertexProcessor = ScanVertexProcessor(metaClient)

    spaceToRead = sys.argv[3]
    vertexReturnCols, edgeReturnCols = getReturnCols(spaceToRead)
    allCols = True
   
    G = nx.Graph()
    if spaceToRead not in metaClient.getPartsAllocFromCache().keys():
        raise Exception('spaceToRead %s is not found in nebula')
    else:
        print('scaning space %s' % spaceToRead)
        scanVertex(spaceToRead, vertexReturnCols, allCols)
        scanEdge(spaceToRead, edgeReturnCols, allCols)
    
    # Run betweenness centrality
    betweenness_dict = nx.betweenness_centrality(G)
    nx.set_node_attributes(G, betweenness_dict, 'betweenness')
    # Run Girvan-NewMan algorithm
    comp = community.girvan_newman(G)
    k = 7
    limited = itertools.takewhile(lambda c: len(c) <= k, comp)
    communities = list(limited)[-1]
    community_dict = {}
    community_num = 0
    for community in communities:
        for character in community:
            community_dict[character] = community_num
        community_num += 1
    nx.set_node_attributes(G, community_dict, 'community')
    nx.write_gexf(G, 'game.gexf')
