#!/bin/bash
set -e

# Setup environment
export PYTHONPATH=/workspaces/AllVibesDemo/pydpvz:$PYTHONPATH
export LD_LIBRARY_PATH=/workspaces/AllVibesDemo/dpvz/src:$LD_LIBRARY_PATH
export VTK_DEFAULT_OPENGL_WINDOW=vtkXOpenGLRenderWindow

PVBATCH="/workspaces/AllVibesDemo/paraview_v610/bin/pvbatch"
MPIEXEC="mpiexec.mpich"
DATA_FILE="output_can_vtpc.dpvtk"
OUT_DIR="day3_slides"
CONFIG="$OUT_DIR/color_eqps.json"
VIEWDIR="[0,1,0]"

echo "Generating animation frames with view direction $VIEWDIR..."
xvfb-run -a $MPIEXEC -np 4 $PVBATCH --sym --force-offscreen-rendering scripts/dpvtkanimate.py --config $CONFIG --viewdirection "$VIEWDIR" $DATA_FILE $OUT_DIR/can_anim_frame

echo "Stitching frames into MP4 with ffmpeg..."
ffmpeg -y -framerate 10 -i $OUT_DIR/can_anim_frame_%04d.png -c:v libx264 -pix_fmt yuv420p $OUT_DIR/can_eqps_animation.mp4

echo "Cleanup temporary frames..."
rm -f $OUT_DIR/can_anim_frame_*.png

echo "Done!"
