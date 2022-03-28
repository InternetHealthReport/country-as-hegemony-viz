#!/usr/bin/env python3
import sys
import re
import json
import ast
import requests
import subprocess

CC=sys.argv[1]
DATE=sys.argv[2]
CC_OF_INTEREST = set()
if len( sys.argv ) > 3:
    CC_OF_INTEREST=set( sys.argv[3].split(',') )

### 1st arg: country
### 2nd arg: date YYYY-MM-DD

prettynames = {} #asn2name
with open("asn-prettynames.txt", 'rt') as inf:
    for line in inf:
        line=line.rstrip('\n')
        f = line.split(' ')
        asn = f[0]
        name = f[1]
        prettynames[ asn ] = line

print( prettynames )

def asn_lookup_cymru( asn ):
    cmd = f"dig +short AS{asn}.asn.cymru.com TXT"
    rv = str( subprocess.check_output( cmd, shell=True ) )
    rv = rv.rstrip("\n")
    fields = list( map( lambda x: re.sub(r"[' \"\n]+",'', x), rv.split('|') ) )
    fields[-1] = fields[-1][:-5] # remove CC and pesky \n
    fields[-1] = re.sub(","," ", fields[-1] )
    print( fields )
    return fields

eyeball_weights = {}
hege_weights = {}

tier1_set = set()
with open("tier1.json") as inf:
    d = json.load( inf )
    for asn in d:
        tier1_set.add( asn )

with open("input-asns.txt") as inf:
    for line in inf:
        if line.startswith('#'):
            # 2nd line is a comment with json with eyeballs ...
            if line.startswith('# {'):
                line = line[2:]
                # it's a python object literal ...
                temp_e = ast.literal_eval( line )
                for k,v in temp_e.iteritems():
                    if v > thres: ### only if over X pct of pop
                        eyeball_weights[ str( k ) ] = v # stringify keys
        elif line.startswith('{'): # different version of the hege code
            continue
            #temp_e = ast.literal_eval( line )
            #for k,v in temp_e.iteritems():
            #    if v > thres: ### only if over X pct of pop
            #        eyeball_weights[ str( k ) ] = v # stringify keys
        else:
            line = line.rstrip('\n')
            f = line.split(', ')
            asn = f[0] # as string!
            hege = float( f[1] )*100
            #if hege > thres:
            hege_weights[ asn ] = hege

eyeball_set = set( eyeball_weights.keys() ) # only record if this is an origin
hege_set = set( hege_weights.keys() ) # only record if this is an origin

print( eyeball_set )
print( hege_set )
print( tier1_set )

stop_set = set() # needed to stop propagation steps

### links
links = set()
nodes = []

### (link all tier1s together)
t1_list = list( tier1_set )
t1_n = len( t1_list )
for idx1 in range(0,t1_n):
    for idx2 in range(idx1,t1_n):
        links.add( ( t1_list[idx1], t1_list[idx2] ) )

prop_from = set()

### initialise the nodes with all we want already
for t1 in tier1_set:
    h_weight = 0
    if t1 in hege_weights:
        h_weight = hege_weights[ t1 ]
    intel = asn_lookup_cymru( t1 )
    nodes.append({
        'id': t1,
        'hege': h_weight,
        'country': 'XX', # ie. not a country. it's a tier1!
        'name': intel[4]
    })
    stop_set.add( t1 )

for hasn in hege_set:
    if hasn in tier1_set: 
        continue # avoid double nodes
    intel = asn_lookup_cymru( hasn )
    hcc = intel[1]
    nodes.append({
        'id': hasn,
        'hege': hege_weights[ hasn ],
        'country': hcc,
        'name': intel[4]
    })
    if hcc == CC:
        prop_from.add( hasn )
    else:
        stop_set.add( hasn )

#for it in range(0,nr_iter): # number iterations
it = 0
while len( prop_from ) > 0:
    print(f"Iteration {it}", file=sys.stderr)
    it += 1
    next_prop_from = set()
    for this_asn in prop_from:
        print(f"propagating for {this_asn}")
        if this_asn in stop_set:
            continue # it has been taken care of
        adj_url = f"https://stat.ripe.net/data/asn-neighbours/data.json?resource={this_asn}&starttime={DATE}"
        print( adj_url )
        r = requests.get( adj_url )
        d = r.json()
        print(f"looping over { len( d['data']['neighbours'] ) } neighbours")
        for n in d['data']['neighbours']:
            links.add( (this_asn, n['asn'] )) # as a tuple
            if not n['asn'] in stop_set:
                stop_set.add( n['asn'] )
                intel = asn_lookup_cymru( n['asn'] )
                ncc = 'ZZ'
                name = ''
                if len( intel ) > 3:
                    ncc = intel[1]
                    name = intel[4]
                nodes.append({
                    'id': n['asn'],
                    'hege': 0,
                    'country': ncc,
                    'name': name,
                })
                if not n['asn'] in tier1_set and n['asn'] == CC:
                    # only propagate if not tier1 or if country is not the origin country
                    # this will make the links to other countries show, but not propagate into the other countries
                    next_prop_from.add( n['asn'] )
    prop_from = next_prop_from

print( it )
print( links )
print( nodes )

def pretty_name( asn, name ):
    if str(asn) in prettynames:
        return f"{prettynames[asn]}"
    else:
        return f"{asn} {name}"
    

with open(f"hege.{CC}.{DATE}.all.gdf",'wt') as outf:
    print("nodedef>name VARCHAR, hege DOUBLE, hegelabel VARCHAR, clabel VARCHAR, label VARCHAR, country VARCHAR", file=outf)
    for n in nodes:
        clabel = 'Other'
        if n['country'] == 'XX':
            clabel = 'Tier1'
        elif n['country'] == CC:
            clabel = CC
        hegelabel = ''
        if n['hege'] > 0:
            hegelabel = pretty_name( n['id'], n['name'] )
        print(f"{n['id']}, {n['hege']}, {hegelabel}, '{clabel}', {n['name']}, {n['country']}", file=outf)
    print("edgedef>node1 VARCHAR,node2 VARCHAR",file=outf)
    for L in links:
        if L[0] != L[1]:
            print(f"{L[0]}, {L[1]}", file=outf)


'''


links_done_set=set()
gw_asns=set()
for link in links:
        # sort for removing duplicates
        slink = tuple(sorted( list( link ) ))
        if not slink in links_done_set:
            out['links'].append({
                'source': link[0],
                'target': link[1]
            })
        links_done_set.add( slink )
        # TODO add 'gateway' designation here
        ltypes=set()
        for l in (link[0], link[1]):
            if l in asn2ann and 'location' in asn2ann[ l ]:
                ltypes.add( asn2ann[ l ]['location'] )
        if ltypes == set(['local','internet']):
            # we found a 'gateway'
            gw_asns.add( link[0] )
            gw_asns.add( link[1] )
print gw_asns
for idx, n in enumerate( out['nodes'] ):
    if n['id'] in gw_asns:
        out['nodes'][ idx ]['gateway'] = True
        
### TODO only add if it's c2p or p2c . for instance only via tier1 club?

print json.dumps( out )
if fmt == 'json':
    with open("./country-as-hegemony.%s.%s.by-pop.json" % (cc,date) ,'w') as outf:
        json.dump( out, outf, indent=2 )
elif fmt == 'gdf':
        #TODO make this work again
        outf = open("output.%s.gdf" % cc ,'w')
        print >>outf, "nodedef>name VARCHAR, hege DOUBLE, eyeball VARCHAR"
        print >>outf, "edgedef>node1 VARCHAR,node2 VARCHAR, directed BOOLEAN"
        # foreach print >>outf, "%s,%s,true" % ( asn, asnl )


nodedef>name VARCHAR, hege DOUBLE, eyeball VARCHAR
8400, 0.2739763644976722, +
31042, 0.14557386749046505, +
3356, 0.11009440349209966, -
15958, 0.073753460629689, +
1299, 0.06220408867756075, -
44143, 0.05026259805588817, +
8447, 0.05026259805588817, -
3257, 0.028099266148440452, -
174, 0.024900456392953452, -
8928, 0.01967750898471613, -
edgedef>node1 VARCHAR,node2 VARCHAR
15958,174
15958,8447
15958,3356
44143,8447
8447,1299
8447,3356
'''

