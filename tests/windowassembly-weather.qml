import Quickshell

import "../services/weather"
import "../widgets/weather"

ShellRoot {
    WeatherService {
        id: weatherService
    }

    SpaceService {
        id: spaceService
    }

    WeatherStationW {
        id: weatherStation

        screen: Quickshell.screens.find(s => s.name === "DP-5")
            || Quickshell.screens[0]

        weatherService: weatherService
        spaceService: spaceService

        menuOpen: true
        currentView: "terminal"
    }
}
