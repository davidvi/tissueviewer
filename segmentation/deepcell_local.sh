export DATA_DIR=${1}
export APPLICATION=mesmer
export NUCLEAR_FILE=${2}

application_file=/home/david/Developer/deepcell-applications/run_app.py

echo python $application_file $APPLICATION \
  --nuclear-image $DATA_DIR/$NUCLEAR_FILE \
  --output-directory $DATA_DIR \
  --output-name masks/${2} \
  --compartment whole-cell \
  --nuclear-channel 0 1 2 \
  --image-mpp 1.0 \
  --squeeze
