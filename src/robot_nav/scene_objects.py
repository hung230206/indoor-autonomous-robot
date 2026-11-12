"""Procedural furniture and slippers, with explicit prior-map opt-in.

Geometry is used to build the physical scene. Only objects marked map_known
contribute to the navigator's prior map; unknown geometry is evaluation-only.
"""
import math


def parts(obj):
    """Local (center, size, color) boxes; metres, floor z=0."""
    kind = obj['kind']
    if kind in ('table', 'chair'):
        table = kind == 'table'
        length, width = ((.72, .60) if table else (.40, .40))
        height = .70 if table else .44
        leg = .045 if table else .030
        result = []
        for x in (-length/2+leg, length/2-leg):
            for y in (-width/2+leg, width/2-leg):
                result.append(((x,y,height/2), (leg,leg,height), '0.25 0.19 0.13'))
        result.append(((0,0,height), (length,width,.035), '0.65 0.40 0.20'))
        if not table:
            result.append(((-length/2+.018,0,.63), (.035,width,.38), '0.32 0.48 0.68'))
        return result
    if kind == 'slipper':
        # Collision approximation of curved strap: three overlapping segments.
        return [((.035,-.037,.027),(.07,.018,.035),'0.12 0.42 0.75'),
                ((.035,.037,.027),(.07,.018,.035),'0.12 0.42 0.75'),
                ((.035,0,.043),(.07,.070,.014),'0.12 0.42 0.75')]
    raise ValueError('Unsupported scene object: '+str(kind))


def sole_points():
    # Rounded, slightly tapered shoe outline, 25 x 10 cm.
    return [( .125*math.cos(a), (.043+.009*math.cos(a))*math.sin(a))
            for a in (i*2*math.pi/20 for i in range(20))]


def _sole_geometry():
    outline=sole_points()
    vertices=[(x,y,z) for z in (0,.018) for x,y in outline]
    faces=[list(reversed(range(20))), list(range(20,40))]
    faces += [[i,(i+1)%20,(i+1)%20+20,i+20] for i in range(20)]
    xyz=', '.join(' '.join(map(str,v)) for v in vertices)
    indices=', '.join(' '.join(map(str,f))+' -1' for f in faces)
    return f'IndexedFaceSet {{ coord Coordinate {{ point [ {xyz} ] }} coordIndex [ {indices} ] }}'


def object_solid(name, obj):
    visual, collision = [], []
    for center,size,color in parts(obj):
        xyz=' '.join(map(str,center)); dims=' '.join(map(str,size))
        geometry=f'Box {{ size {dims} }}'
        visual.append(f'Pose {{ translation {xyz} children [ Shape {{ appearance PBRAppearance {{ baseColor {color} roughness 1 metalness 0 }} geometry {geometry} }} ] }}')
        collision.append(f'Pose {{ translation {xyz} children [ {geometry} ] }}')
    if obj['kind']=='slipper':
        geometry=_sole_geometry()
        visual.append(f'Shape {{ appearance PBRAppearance {{ baseColor .08 .14 .23 roughness 1 metalness 0 }} geometry {geometry} }}')
        collision.append(geometry)
    return f'''DEF {name} Solid {{
      translation {obj['x_m']} {obj['y_m']} 0
      rotation 0 0 1 {obj.get('yaw_rad',0)}
      name "{name}_{obj['kind']}"
      children [ {' '.join(visual)} ]
      boundingObject Group {{ children [ {' '.join(collision)} ] }}
    }}'''


def prior_rectangles(objects):
    """Conservative rotated AABBs at robot height; no solid table footprint."""
    result=[]
    for obj in objects:
        if not obj.get('map_known',False):
            continue
        boxes=parts(obj)
        if obj['kind']=='slipper':
            boxes=boxes+[((0,0,.009),(.25,.105,.018),'')]
        yaw=obj.get('yaw_rad',0); co,si=math.cos(yaw),math.sin(yaw)
        for (x,y,z),(length,width,height),_ in boxes:
            # Entire present rig is below .35m; high seats/tops are passable.
            if z-height/2>.35:
                continue
            cx=obj['x_m']+co*x-si*y; cy=obj['y_m']+si*x+co*y
            dx=(abs(co)*length+abs(si)*width)/2
            dy=(abs(si)*length+abs(co)*width)/2
            result.append((cx-dx,cy-dy,cx+dx,cy+dy))
    return result


def object_contacts(nodes):
    """Evaluation only: static props can contact the dynamic robot in this scene.

    Query the props themselves, avoiding robot/floor and caster contacts.
    These contacts never populate the map or serve as perception inputs.
    """
    return [{'object':name,'point_m':list(point.point)}
            for name,node in nodes for point in node.getContactPoints()]
