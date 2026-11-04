cmake_minimum_required(VERSION 3.21)
project(PostApolloCompanyVectorProbe LANGUAGES CXX)
# Isolated Qt6 process, NEVER imported into Quickshell.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.5 REQUIRED COMPONENTS Quick Location Positioning)
find_package(QMapLibre 3.0 REQUIRED COMPONENTS Location)
qt_standard_project_setup()

qt_add_executable(company-vector-probe main.cpp)
qt_add_qml_module(company-vector-probe
    URI CompanyVectorProbe
    VERSION 1.0
    RESOURCE_PREFIX "/"
    QML_FILES main.qml
)
target_compile_definitions(company-vector-probe PRIVATE
    COMPANY_PROBE_STYLE_PATH="${CMAKE_CURRENT_SOURCE_DIR}/style-fixture.json"
    COMPANY_PROBE_ONLINE_STYLE_PATH="${CMAKE_CURRENT_SOURCE_DIR}/style-post-apollo-online.json"
)
target_link_libraries(company-vector-probe PRIVATE
    Qt6::Quick Qt6::Location Qt6::Positioning QMapLibre::Location
)
qmaplibre_location_setup_plugins(company-vector-probe)
