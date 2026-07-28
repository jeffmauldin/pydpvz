#ifndef PYDPVZ_MPI_CASTER_H
#define PYDPVZ_MPI_CASTER_H

#include <pybind11/pybind11.h>
#include <mpi.h>

#if defined(DPVZ_MPI)
// Include mpi4py C-API headers if available, or convert via integer handles
#include <mpi4py/mpi4py.h>
#endif

namespace pybind11 { namespace detail {

template <>
struct type_caster<MPI_Comm> {
public:
    PYBIND11_TYPE_CASTER(MPI_Comm, _("mpi4py.MPI.Comm"));

    bool load(handle src, bool) {
        if (src.is_none()) {
            value = MPI_COMM_WORLD;
            return true;
        }

        // Try extracting via pybind11 attribute check for mpi4py Comm object
        if (hasattr(src, "py2f")) {
            py::object py2f_func = src.attr("py2f");
            py::object fort_handle = py2f_func();
            MPI_Fint f_comm = fort_handle.cast<MPI_Fint>();
            value = MPI_Comm_f2c(f_comm);
            return true;
        }

        // Fallback: try casting directly from integer handle if passed as int
        try {
            MPI_Fint f_comm = src.cast<MPI_Fint>();
            value = MPI_Comm_f2c(f_comm);
            return true;
        } catch (...) {
            return false;
        }
    }

    static handle cast(MPI_Comm src, return_value_policy /* policy */, handle /* parent */) {
        if (import_mpi4py() < 0) {
            PyErr_SetString(PyExc_ImportError, "Could not import mpi4py");
            return nullptr;
        }
        MPI_Fint f_comm = MPI_Comm_c2f(src);
        py::module_ mpi_mod = py::module_::import("mpi4py.MPI");
        py::object comm_cls = mpi_mod.attr("Comm");
        py::object f2py_func = comm_cls.attr("f2py");
        py::object py_comm = f2py_func(f_comm);
        return py_comm.release();
    }
};

}} // namespace pybind11::detail

#endif // PYDPVZ_MPI_CASTER_H
