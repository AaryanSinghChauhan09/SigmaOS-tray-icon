    # SigmaOS-tray-icon

    System tray icon host (XAppStatusIcon)

    Part of the **SigmaOS** sovereign operating-system ecosystem — a multi-repository
    distribution modelled on Linux Mint and Omarchy Linux. See the parent
    [`SigmaOS`](https://github.com/AaryanSinghChauhan09/SigmaOS) repository for the
    full component index.

    ## Upstream inspirations
    - https://github.com/linuxmint/rhythmbox-tray-icon

    ## Design principles applied
    - **Encapsulation**
- **Information Hiding**
- **Fail-Fast**
- **KISS**
- **Separation of Concerns**
- **Deterministic Testing**

    ## Usage
    Verbs: `register, icon, menu, emit`

    ```
    $ sigma-tray register rhythmbox --icon media-player
$ sigma-tray icon rhythmbox --set media-player-paused
$ sigma-tray menu rhythmbox --item "play:Play" --item "pause:Pause"
$ sigma-tray emit rhythmbox --event menu-action --payload play

    ```

    ## Build & test
    ```
    make build
    make test
    ```

    ## Licence
    GNU General Public License v3.0 (FOSS).
