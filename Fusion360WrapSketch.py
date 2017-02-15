#Author-Hans Kellner
#Description-Wrap a 2d sketch around a cylinder
#
# Assumes sketch is on XY plane and cylinder is oriented with axis aligned with Z up
#
import adsk.core, adsk.fusion, adsk.cam, traceback, math

app = None
ui  = None
design = None

commandId = 'Fusion360WrapSketch'
commandName = 'Wrap Sketch'
commandDescription = 'Wrap 2D sketch curves around a cylinder.'
commandResources = './/Resources//Fusion360WrapSketch'
commandToolClip = './/Toolclip//Fusion360WrapSketch.png'

# Global set of event handlers to keep them referenced for the duration of the command
handlers = []

# Inputs
sketch_selInput = None
cylinder_selInput = None
xscale_float_spinnerInput = None
yscale_float_spinnerInput = None
radiusOffset_float_spinnerInput = None
thickenDepth_float_spinnerInput = None
splitFace_boolinput = None

def point3DStr(pt):
    return (str(pt.x) + ',' + str(pt.y) + ',' + str(pt.z))

def getSketchCurvesBoundingBox():
    bbox = None
    if sketch_selInput != None:
        for i in range(sketch_selInput.selectionCount):
            sel = sketch_selInput.selection(i)
            if bbox == None:
                bbox = sel.entity.boundingBox.copy()
            else:
                bbox.combine(sel.entity.boundingBox)

    return bbox

def mapPoint2Curve(x, y, radius, xOrig, yOrig, zOrig):
    x2 = radius * math.cos(x / radius) + xOrig
    y2 = radius * math.sin(x / radius) + yOrig
    z2 = y + zOrig
    return x2, y2, z2

def wrapSketch(cylSelInput, sketchSelInput):
    if cylSelInput == None or sketchSelInput == None or design == None:
        return

    if sketchSelInput.selectionCount < 1 or cylSelInput.selectionCount != 1:
        return

    xScale = 1.0
    if xscale_float_spinnerInput != None:
        xScale = xscale_float_spinnerInput.value

    yScale = 1.0
    if yscale_float_spinnerInput != None:
        yScale = yscale_float_spinnerInput.value

    radiusOffset = 0.1
    if radiusOffset_float_spinnerInput != None:
        radiusOffset = radiusOffset_float_spinnerInput.value

    thickenDepth = 0.2
    if thickenDepth_float_spinnerInput != None:
        thickenDepth = thickenDepth_float_spinnerInput.value
        
    # Creating a sketch will empty the selection input.  Cache the selected entities
    # so we don't lose access to them when new sketch created.
    sketchCurves = []
    for i in range(sketchSelInput.selectionCount):
        sketchCurves.append(sketchSelInput.selection(i).entity)

    # cache cylinder face
    cylFace = cylSelInput.selection(0).entity

    try:
        # Get the root component of the active design.
        rootComp = design.rootComponent
        # Create a new sketch on the xy plane.
        sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        sketch.name = 'WrapSketch'

        cylGeom = cylFace.geometry

        # Collection of curves to use as splitting tools
        splitToolObjCol = adsk.core.ObjectCollection.create()

        # Iterate over the sketch curves
        for sketchCurve in sketchCurves:
            obj_type = sketchCurve.objectType

            if obj_type == 'adsk::fusion::SketchArc':
                print('SketchArc : unsupported')
            elif obj_type == 'adsk::fusion::SketchCircle':
                print('SketchCircle : unsupported')
            elif obj_type == 'adsk::fusion::SketchEllipse':
                print('SketchEllipse : unsupported')
            elif obj_type == 'adsk::fusion::SketchEllipticalArc':
                print('SketchEllipticalArc : unsupported')
            elif obj_type == 'adsk::fusion::SketchFittedSpline':
                #print('SketchFittedSpline')
                # Get this splines points
                fitPoints = sketchCurve.fitPoints

                # Create an object collection for the points.
                newFitPoints = adsk.core.ObjectCollection.create()

                for ip in range(fitPoints.count):
                    pt = fitPoints.item(ip).geometry
                    # map the old point to cylinder
                    xNew, yNew, zNew = mapPoint2Curve(pt.x * xScale, pt.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, 0)
                    newFitPoints.add(adsk.core.Point3D.create(xNew, yNew, zNew)) #cylGeom.origin.z + zNew))  origin is in middle of cylinder.  Need to find length and offset.

                # Create the spline.
                newFittedSpline = sketch.sketchCurves.sketchFittedSplines.add(newFitPoints)
                if newFittedSpline != None:
                    newFittedSpline.isClosed = sketchCurve.isClosed

                # Split the face with this spline?
                if splitFace_boolinput != None and splitFace_boolinput.value:
                    splitToolObjCol.add(newFittedSpline)

            elif obj_type == 'adsk::fusion::SketchFixedSpline':
                print('SketchFixedSpline : unsupported')
                # TODO Convert fixed to fitted spline
            elif obj_type == 'adsk::fusion::SketchLine':
                #print('SketchLine')
                # Convert line to arc on cylinder face
                ptStart = sketchCurve.startSketchPoint.geometry
                ptEnd   = sketchCurve.endSketchPoint.geometry
                
                # map the points to cylinder
                xStart, yStart, zStart = mapPoint2Curve(ptStart.x * xScale, ptStart.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, 0)
                xEnd, yEnd, zEnd = mapPoint2Curve(ptEnd.x * xScale, ptEnd.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, 0)
                
                # Check for a vertical line which will just map to a line
                if ptStart.x == ptEnd.x:
                    lines = sketch.sketchCurves.sketchLines
                    lines.addByTwoPoints(adsk.core.Point3D.create(xStart, yStart, zStart), adsk.core.Point3D.create(xEnd, yEnd, zEnd))
                else:
                    # mapping to a cylinder so create an arc
                    xCtr, yCtr, zCtr = mapPoint2Curve(((ptStart.x + ptEnd.x) / 2.0) * xScale, ((ptStart.y + ptEnd.y) / 2.0) * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, 0)
                    
                    sketchArcs = sketch.sketchCurves.sketchArcs
                    sketchArcs.addByThreePoints(adsk.core.Point3D.create(xStart, yStart, zStart),
                                                adsk.core.Point3D.create(xCtr, yCtr, zCtr),
                                                adsk.core.Point3D.create(xEnd, yEnd, zEnd))
                
            elif obj_type == 'adsk::fusion::SketchPoint':
                #print('SketchPoint')
                pt = sketchCurve.geometry
                
                # map the point to cylinder
                xNew, yNew, zNew = mapPoint2Curve(pt.x * xScale, pt.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, 0)
                
                sketchPoints = sketch.sketchPoints
                sketchPoints.add(adsk.core.Point3D.create(xNew, yNew, zNew))
            else:
                print('Sketch type unsupported: ' + obj_type)

        # Split the face with curves?
        if splitFace_boolinput != None and splitFace_boolinput.value:

            # TODO : Split API doesn't allow setting Split Type with API.  Use patches for now.
#==============================================================================
#             # Get SplitFaceFeatures
#             splitFaceFeats = rootComp.features.splitFaceFeatures
# 
#             # Set faces to split
#             objCol = adsk.core.ObjectCollection.create()
#             objCol.add(cylFace)
# 
#             # Create SplitFaceFeatureInput
#             splitFaceInput = splitFaceFeats.createInput(objCol, splitToolObjCol, True)
#             #splitFaceInput.splittingTool = splitToolObjCol
# 
#             # Create split face feature
#             splitFaceFeats.add(splitFaceInput)
#==============================================================================

            # Create patches for each of the curves. Then thicken the patches
            # to create new bodies. 
            patches = rootComp.features.patchFeatures
            newPatches = []
            
            for iCurve in range(splitToolObjCol.count):
                curve = splitToolObjCol.item(iCurve)
                patchInput = patches.createInput(curve, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                newPatch = patches.add(patchInput)
                if newPatch != None:
                    newPatches.append(newPatch)
                    
            # Thicken patch features
            thickenFeatures = rootComp.features.thickenFeatures
            for aPatch in newPatches:
                bodies = aPatch.bodies
                inputSurfaces = adsk.core.ObjectCollection.create()
                for body in bodies:
                    inputSurfaces.add(body)

                thickness = adsk.core.ValueInput.createByReal(thickenDepth)
                thickenInput = thickenFeatures.createInput(inputSurfaces, thickness, False,  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                thickenFeatures.add(thickenInput)
        
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class MyCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            if sketch_selInput == None or cylinder_selInput == None or sketch_selInput.selectionCount < 1 or cylinder_selInput.selectionCount != 1:
                return

            cylGeom = cylinder_selInput.selection(0).entity.geometry
            print('Cylinder Selected:')
            print('  origin = ' + point3DStr(cylGeom.origin))
            print('  radius = ' + str(cylGeom.radius))
            print('  axis   = ' + point3DStr(cylGeom.axis))

            # Iterate over the sketch curves
            print('Selected Sketch curves:')
            for i in range(sketch_selInput.selectionCount):
                sketch_entity = sketch_selInput.selection(i).entity
                obj_type = sketch_entity.objectType
                print('  (' + str(i) + ') Type = ' + obj_type)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Event handler for the validateInputs event.
class MyValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        validateInputsEventArgs = adsk.core.ValidateInputsEventArgs.cast(args)
        validateInputsEventArgs.areInputsValid = sketch_selInput != None and cylinder_selInput != None and sketch_selInput.selectionCount >= 1 and cylinder_selInput.selectionCount == 1

# Event handler for the execute event.
class MyExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs
            if inputs != None:
                sketchSelInput = inputs.itemById(commandId + '_sketch_selection')
                if sketchSelInput == None:
                    return
                cylSelInput = inputs.itemById(commandId + '_cylinder_selection')
                if cylSelInput == None:
                    return

            wrapSketch(cylSelInput, sketchSelInput)

        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class MyCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            adsk.terminate()
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class MyCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            cmd = args.command

            onDestroy = MyCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            handlers.append(onDestroy)

            onInputChanged = MyCommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            handlers.append(onInputChanged)

            onValidateInputs = MyValidateInputsHandler()
            cmd.validateInputs.add(onValidateInputs)
            handlers.append(onValidateInputs)

            onExecute = MyExecuteHandler()
            cmd.execute.add(onExecute)
            handlers.append(onExecute)

            inputs = cmd.commandInputs
            global commandId

            # Create cylinder selection input
            global cylinder_selInput
            cylinder_selInput = inputs.addSelectionInput(commandId + '_cylinder_selection', 'Select cylinder', 'Select cylinder face')
            cylinder_selInput.setSelectionLimits(1,1)
            cylinder_selInput.addSelectionFilter('CylindricalFaces')

            # Create sketch curve selection input
            global sketch_selInput
            sketch_selInput = inputs.addSelectionInput(commandId + '_sketch_selection', 'Select sketch curves', 'Select sketch curves')
            sketch_selInput.setSelectionLimits(1,0)
            sketch_selInput.addSelectionFilter('SketchCurves') # includes lines and splines
            sketch_selInput.addSelectionFilter('SketchPoints')

            # Create float spinner input
            global xscale_float_spinnerInput
            xscale_float_spinnerInput = inputs.addFloatSpinnerCommandInput(commandId + '_scaleX_spinnerFloat', 'X Scale', 'cm', 0.01 , 10.0 , 0.25, 1)
            
            global yscale_float_spinnerInput
            yscale_float_spinnerInput = inputs.addFloatSpinnerCommandInput(commandId + '_scaleY_spinnerFloat', 'Y Scale', 'cm', 0.01 , 10.0 , 0.25, 1)
            
            global splitFace_boolinput
            splitFace_boolinput = inputs.addBoolValueInput(commandId + '_splitFace', 'Split Cylinder Face', True, '', False) # TODO: No way to set Split Type with API.  Needed for splits to work.

            global radiusOffset_float_spinnerInput
            radiusOffset_float_spinnerInput = inputs.addFloatSpinnerCommandInput(commandId + '_radiusOffset_spinnerFloat', 'Radius Offset', 'cm', -100.0 , 100.0 , 0.1, 0.1)

            global thickenDepth_float_spinnerInput
            thickenDepth_float_spinnerInput = inputs.addFloatSpinnerCommandInput(commandId + '_thickenDepth_spinnerFloat', 'Thicken Depth', 'cm', -100.0 , 100.0 , 0.1, 0.2)
            
        except:
            if ui:
                ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def run(context):
    try:
        global app
        global ui
        global design

        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = app.activeProduct

        # Create command definition
        cmdDef = ui.commandDefinitions.itemById(commandId)
        if not cmdDef:
            cmdDef = ui.commandDefinitions.addButtonDefinition(commandId, commandName, commandDescription, commandResources)
            commandDef.toolClipFilename = commandToolClip

        # Add command created event
        onCommandCreated = MyCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        # Keep the handler referenced beyond this function
        handlers.append(onCommandCreated)

        
        # Get the ADD-INS panel in the model workspace. 
        addInsPanel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')

        # Add the button to the bottom.
        buttonControl = addInsPanel.controls.addCommand(cmdDef)

        # Make the button available in the panel.
        buttonControl.isPromotedByDefault = True
        buttonControl.isPromoted = True        
        
        # Execute command
        cmdDef.execute()

        # Prevent this module from being terminate when the script returns, because we are waiting for event handlers to fire
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        #ui.messageBox('Stop addin')

        cmdDefs = ui.commandDefinitions

        # Delete the button definition.
        cmdDef = ui.commandDefinitions.itemById(commandId)
        if cmdDef:
            cmdDef.deleteMe()

        # Get panel the control is in.
        addInsPanel = ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')

        # Get and delete the button control.
        buttonControl = addInsPanel.controls.itemById(commandId)
        if buttonControl:
            buttonControl.deleteMe()
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
