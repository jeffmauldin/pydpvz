cmake_minimum_required(VERSION 3.15)
project(pydpvz LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(MPI REQUIRED)
find_package(pybind11 REQUIRED)
find_package(ZLIB REQUIRED)

set(DPVZ_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../dpvz/src")

include_directories(
    ${DPVZ_SRC_DIR}
    ${MPI_CXX_INCLUDE_PATH}
)

add_definitions(-DDPVZ_MPI)

pybind11_add_module(_pydpvz
    src/main_bindings.cpp
    ${DPVZ_SRC_DIR}/DPvzErr.C
    ${DPVZ_SRC_DIR}/DPvzFile.C
    ${DPVZ_SRC_DIR}/DPvzGlobal.C
    ${DPVZ_SRC_DIR}/DPvzMetadata.C
    ${DPVZ_SRC_DIR}/DPvzMode.C
    ${DPVZ_SRC_DIR}/DPvzRankToc.C
    ${DPVZ_SRC_DIR}/DPvzToc.C
    ${DPVZ_SRC_DIR}/DPvzTocEntry.C
    ${DPVZ_SRC_DIR}/DPvzTocIndex.C
    ${DPVZ_SRC_DIR}/DPvzUtil.C
    ${DPVZ_SRC_DIR}/DPvzVtk.C
    ${DPVZ_SRC_DIR}/DPvzVtkData.C
)

target_link_libraries(_pydpvz PRIVATE
    MPI::MPI_CXX
    ZLIB::ZLIB
)
