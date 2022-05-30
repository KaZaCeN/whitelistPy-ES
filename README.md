# whitelistPy-ES

Whitelist Manager es un bot diseñado para ayudar en la recolección de direcciones de wallet para whitelists o drops de NFTs.
Tras configurar el bot, los usuarios con el rol seleccionado podrán registrar las direcciones de sus wallets, las cuales podrás descargar luego en formato CSV.
Nota, la configuración debe estar completa para que el bot funcione.

## COMANDOS
Nota: deberás ser administrador para acceder a la mayoría de los comandos.

**>channel #NombreDelCanal**: Selecciona el canal en el que el bot leerá las direcciones de wallets.

**>role @NombreDelRol**: Selecciona el rol que debe poseer un usuario para poder añadir su wallet al registro de la whitelist.

**>blockchain eth/sol/ada/matic**: Selecciona en que blockchain se va a trabajar. Esto permitira validar las direcciones de wallets que se añadan.

**>config**: Ver la configuración actual del servidor.

**>data**: Obtener la whitelist completa en formato CSV.

**>clear**: Limpia la configuración y los datos de este servidor.

**>check**: Te dirá si la durección de tu wallet ha sido registrada o no.

**>help**: Pantalla de ayuda para usuarios.

**>help.admin**: Pantalla de ayuda para administradores.

## USO

To run your own instance of this bot:
1. Instala python 3.7+
2. `cd` into the directory and run `python -m pip install -r requirements.txt`
3. Set the `ACCESS_TOKEN` environment variable:
    - If you're on linux or mac: `export ACCESS_TOKEN=<your discord application access token here>`
    - If you're on windows: `$Env:ACCESS_TOKEN = "<your discord application access token here>"`
4. `python main.py`