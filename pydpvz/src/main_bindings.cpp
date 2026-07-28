#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <mpi.h>

#include "DPvzFile.h"
#include "DPvzVtk.h"

namespace py = pybind11;

static MPI_Comm extract_mpi_comm(py::object comm_obj) {
    if (comm_obj.is_none()) {
        return MPI_COMM_WORLD;
    }
    if (py::hasattr(comm_obj, "py2f")) {
        py::object py2f_func = comm_obj.attr("py2f");
        MPI_Fint f_comm = py2f_func().cast<MPI_Fint>();
        return MPI_Comm_f2c(f_comm);
    }
    try {
        MPI_Fint f_comm = comm_obj.cast<MPI_Fint>();
        return MPI_Comm_f2c(f_comm);
    } catch (...) {
        return MPI_COMM_WORLD;
    }
}

PYBIND11_MODULE(_pydpvz, m) {
    m.doc() = "pydpvz: Python bindings for Sandia National Laboratories DPvz parallel I/O library";

    // Bind DPvzMode Enum
    py::enum_<DPvzMode>(m, "DPvzMode")
        .value("DPvzReadOnly", DPvzReadOnly)
        .value("DPvzReadWrite", DPvzReadWrite)
        .value("DPvzCreate", DPvzCreate)
        .value("DPvzReplace", DPvzReplace)
        .export_values();

    // Bind DPvzTocEntry struct
    py::class_<DPvzTocEntry>(m, "DPvzTocEntry")
        .def(py::init<>())
        .def_readwrite("cycle", &DPvzTocEntry::cycle)
        .def_readwrite("time", &DPvzTocEntry::time)
        .def_readwrite("ranks", &DPvzTocEntry::ranks)
        .def_readwrite("offset", &DPvzTocEntry::offset)
        .def("__repr__", [](const DPvzTocEntry& e) {
            return "<DPvzTocEntry cycle=" + std::to_string(e.cycle) +
                   " time=" + std::to_string(e.time) +
                   " ranks=" + std::to_string(e.ranks) + ">";
        });

    // Bind DPvzRankToc struct
    py::class_<DPvzRankToc>(m, "DPvzRankToc")
        .def(py::init<>())
        .def_readwrite("inflated_size", &DPvzRankToc::inflated_size)
        .def_readwrite("deflated_size", &DPvzRankToc::deflated_size)
        .def_readwrite("deflated_crc", &DPvzRankToc::deflated_crc)
        .def_readwrite("offset", &DPvzRankToc::offset)
        .def("__repr__", [](const DPvzRankToc& r) {
            return "<DPvzRankToc offset=" + std::to_string(r.offset) +
                   " deflated_size=" + std::to_string(r.deflated_size) +
                   " inflated_size=" + std::to_string(r.inflated_size) + ">";
        });

    // Bind DPvzFile class
    py::class_<DPvzFile>(m, "DPvzFile")
        .def(py::init([](std::string name, DPvzMode mode, uint64_t g_sz, std::string majik, std::string ext, py::object comm_obj, bool repair, int root) {
            MPI_Comm comm = extract_mpi_comm(comm_obj);
            return new DPvzFile(name, mode, g_sz, majik, ext, comm, repair, root);
        }), py::arg("name"), py::arg("mode"), py::arg("g_sz") = 0, py::arg("majik") = DPVTK_MAJIK, py::arg("ext") = DPVTK_EXT,
            py::arg("comm") = py::none(), py::arg("repair") = false, py::arg("root") = 0)

        .def("get_page_size", &DPvzFile::get_page_size)
        .def("get_global_size", &DPvzFile::get_global_size)
        .def("get_steps", &DPvzFile::get_steps)
        .def("get_map", [](DPvzFile& self) {
            int64_t steps = self.get_steps();
            std::vector<DPvzTocEntry> map_vec(steps);
            if (steps > 0) {
                self.get_map(map_vec.data());
            }
            return map_vec;
        })
        .def("get_step_rank", &DPvzFile::get_step_rank, py::arg("step"), py::arg("rank"))
        .def("get_step_toc", [](DPvzFile& self, DPvzTocEntry& step) {
            std::vector<DPvzRankToc> rank_toc(step.ranks);
            if (step.ranks > 0) {
                self.get_step_toc(step, rank_toc.data());
            }
            return rank_toc;
        })
        .def("get_data", [](DPvzFile& self, DPvzRankToc& step_rank) {
            std::string buf(step_rank.inflated_size, '\0');
            bool err = self.get_data(step_rank, &buf[0]);
            if (err) {
                throw std::runtime_error("DPvzFile::get_data failed");
            }
            // Trim to actual inflated size (no trailing nulls)
            return py::bytes(buf.data(), step_rank.inflated_size);
        })
        .def("write", [](DPvzFile& self, int64_t cycle, double time, py::bytes data, int32_t root) {
            std::string str_data = data;
            return self.write(cycle, time, str_data.data(), str_data.size(), root);
        }, py::arg("cycle"), py::arg("time"), py::arg("data"), py::arg("root") = 0)
        .def("truncate", [](DPvzFile& self, int64_t idx, int32_t root) {
            return self.truncate(idx, root);
        }, py::arg("idx"), py::arg("root") = 0)
        .def("truncate_time", [](DPvzFile& self, int64_t cycle, double time, int32_t root) {
            return self.truncate(cycle, time, root);
        }, py::arg("cycle"), py::arg("time"), py::arg("root") = 0)
        .def("active_entries", &DPvzFile::active_entries)
        .def("failed", &DPvzFile::failed)
        .def_readwrite("file_name", &DPvzFile::file_name);

    // Bind DPvzVtk subclass
    py::class_<DPvzVtk, DPvzFile>(m, "DPvzVtk")
        .def(py::init([](std::string name, DPvzMode mode, py::object comm_obj, bool repair) {
            MPI_Comm comm = extract_mpi_comm(comm_obj);
            return new DPvzVtk(name, mode, comm, repair);
        }), py::arg("name"), py::arg("mode"), py::arg("comm") = py::none(), py::arg("repair") = false)

        .def_static("list", [](const char* file, const char* path) {
            return DPvzVtk::list(stdout, file, path);
        }, py::arg("file"), py::arg("path") = ".")
        .def_static("extract", [](const char* file, const char* path) {
            return DPvzVtk::extract(file, path);
        }, py::arg("file"), py::arg("path") = ".")
        .def_static("show", [](const char* file, const char* path) {
            return DPvzVtk::show(stdout, file, path);
        }, py::arg("file"), py::arg("path") = ".");
}
