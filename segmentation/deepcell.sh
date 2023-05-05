export DATA_DIR=${1}
export MOUNT_DIR=/data
export APPLICATION=mesmer
export NUCLEAR_FILE=${2}

docker run -it --gpus 1 \
  -v $DATA_DIR:$MOUNT_DIR \
  vanvalenlab/deepcell-applications:latest-gpu \
  $APPLICATION \
  --nuclear-image $MOUNT_DIR/$NUCLEAR_FILE \
  --output-directory $MOUNT_DIR \
  --output-name masks/${2} \
  --compartment whole-cell \
  --nuclear-channel 0 1 2 \
  --image-mpp 1.0 \
  --squeeze
