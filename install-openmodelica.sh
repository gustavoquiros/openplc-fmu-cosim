
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

curl -fsSL http://build.openmodelica.org/apt/openmodelica.asc | sudo tee /etc/apt/trusted.gpg.d/openmodelica-keyring.asc

sudo chmod a+r /etc/apt/trusted.gpg.d/openmodelica-keyring.asc

echo "deb [arch=amd64 signed-by=/etc/apt/trusted.gpg.d/openmodelica-keyring.asc] \
  https://build.openmodelica.org/apt \
  $(cat /etc/os-release | grep "\(UBUNTU\\|DEBIAN\\|VERSION\)_CODENAME" | sort | cut -d= -f 2 | head -1) \
  stable" | sudo tee /etc/apt/sources.list.d/openmodelica.list
  
sudo apt update && sudo apt install openmodelica
  
#gpg --keyserver keyserver.ubuntu.com --recv-keys 3A59B53664970947
#gpg --export --armor 3A59B53664970947 | sudo tee /etc/apt/trusted.gpg.d/openmodelica-keyring.asc && sudo apt-get update 

