import pytest
import numpy as np
import numpy.testing as npt

from ..utils import rfactor_compute, _fitting_nnls, _fitting_admm, fitting_spectrum

# ------------------------------------------------------------------------------
#  useful functions for generating of datasets for testing of fitting algorithms

def _generate_gaussian_spectra(x_values, gaussian_centers, gaussian_std):

    assert len(gaussian_centers) == len(gaussian_std), \
        "The number of center values must be equal to the number of STD values"
    nn = len(x_values)
    n_spectra = len(gaussian_centers)

    spectra = np.zeros(shape=[nn, len(gaussian_centers)])
    for n in range(n_spectra):
        p, std = gaussian_centers[n], gaussian_std[n]
        spectra[:, n] = np.exp(-np.square(x_values - p) / (2 * std ** 2))

    return spectra

class DataForFittingTest:
    """
    The class that generates and stores dataset used for testing of fitting algorithms
    """
    def __init__(self, **kwargs):
        self.spectra = None
        self.weights = None
        self.data_input = None

        self.generate_dataset(**kwargs)

    def generate_dataset(self, *, n_pts = 101, pts_range=(0, 100),
                         n_spectra = 3, n_gaus_centers_range=(20,80), gauss_std_range=(10, 20),
                         weights_range=(0.1, 1), n_data_dimensions=(8,), axis=0):

        if n_data_dimensions:
            data_dim = n_data_dimensions
        else:
            data_dim = (1,)

        # Values for 'energy' axis
        self.x_values = np.mgrid[pts_range[0]: pts_range[1]: n_pts * 1j]

        # Centers of gaussians are evenly spread in the range
        gaussian_centers = np.mgrid[n_gaus_centers_range[0]: n_gaus_centers_range[1]: n_spectra * 1j]
        # Standard deviations are uniformly distributed in the range
        gaussian_std = np.random.rand(n_spectra) * \
                       (gauss_std_range[1] - gauss_std_range[0]) + gauss_std_range[0]

        self.spectra = _generate_gaussian_spectra(x_values=self.x_values,
                                                 gaussian_centers=gaussian_centers,
                                                 gaussian_std=gaussian_std)

        # The number of pixels in the flattened multidimensional image
        dims = np.prod(data_dim)
        # Generate data for every pixel of the multidimensional image
        self.weights = np.random.rand(n_spectra, dims) * \
                       (weights_range[1] - weights_range[0]) + weights_range[0]
        self.data_input = np.matmul(self.spectra, self.weights)

        if n_data_dimensions:
            # Convert weights and data from 2D to multidimensional arrays
            self.weights = np.reshape(self.weights, np.insert(data_dim, 0, n_spectra))
            self.data_input = np.reshape(self.data_input, np.insert(data_dim, 0, n_pts))

            if axis:  # If axis != 0
                # Create copy of the array (np.moveaxis creates view of the array)
                self.weights = np.array(np.moveaxis(self.weights, 0, axis))
                self.data_input = np.array(np.moveaxis(self.data_input, 0, axis))
        else:
            # Convert weights and data to 1D arrays representing a single point
            self.weights = np.squeeze(self.weights, axis=1)
            self.data_input = np.squeeze(self.data_input, axis=1)

    def validate_output_weights(self, weights_output, decimal=10):

        assert weights_output.shape == self.weights.shape, \
            f"Shapes of the output weight array {weights_output.shape} and "\
            f" input weight array {self.weights.shape} do not match. Can not compare the arrays"

        # Check if the weights match
        npt.assert_array_almost_equal(
            weights_output, self.weights, decimal=decimal,
            err_msg="Estimated weights do not match the weights used for dataset generation")


def test_rfactor_compute():
    r"""
    Basic test for 'rfactor_compute' function. Performed once on a random dataset.
    """
    n_pts = 100
    n_refs = 5

    # Matrix with reference spectra
    ref_spectra = np.random.randn(n_pts, n_refs)
    # Weights
    fit_results = np.random.randn(n_refs)
    # Observed data (pure, no residual)
    b = np.matmul(ref_spectra, fit_results)
    # Residual
    res = np.random.randn(n_pts)
    spectrum = b + res

    # This is the equation used to compute R-factor
    rfactor_expected = sum(abs(res))/sum(abs(spectrum))

    # Now call the function
    rfactor = rfactor_compute(spectrum, fit_results, ref_spectra)

    npt.assert_almost_equal(
        rfactor, rfactor_expected,
        err_msg=f"Error in evaluating R-factor: {rfactor}, expected is {rfactor_expected}")


def test_rfactor_compute_fail():
    r"""
    Function rfactor_compute. Test the cases that will cause the function to fail.
    """

    n_pts = 100
    n_refs = 5

    # There will be no computations performed, so all zeros are good enough
    ref_spectra = np.zeros(shape=[n_pts, n_refs])
    fit_results = np.zeros(shape=[n_refs])
    spectrum = np.zeros(shape=[n_pts])

    # Wrong dimensions of parameter 'spectrum'
    with pytest.raises(AssertionError, match="must be 1D array"):
        rfactor_compute(ref_spectra, fit_results, ref_spectra)
    # Wrong dimensions of parameter 'fit_results'
    with pytest.raises(AssertionError, match="must be 1D array"):
        rfactor_compute(spectrum, ref_spectra, ref_spectra)
    # Wrong dimensions of parameter 'ref_spectra'
    with pytest.raises(AssertionError, match="must be 2D array"):
        rfactor_compute(spectrum, fit_results, fit_results)
    # Mismatch between the number of data points
    with pytest.raises(AssertionError, match="must have the same number of data points"):
        rfactor_compute(np.delete(spectrum, -1), fit_results, ref_spectra)
    # Mismatch between the number of spectrum points
    with pytest.raises(AssertionError, match="must have the same number of spectrum points"):
        rfactor_compute(spectrum, np.delete(fit_results, -1), ref_spectra)


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (8,)},
    {"n_data_dimensions": (15,)},
])
def test_fitting_nnls(dataset_params):

    fitting_data = DataForFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # -------------- Test regular fitting ---------------
    weights_estimated, rfactor, residual = _fitting_nnls(data_input, spectra)

    fitting_data.validate_output_weights(weights_estimated, decimal=10)

    # Validate 'rfactor' and 'residual' (do it for a single point)
    data_fitted = np.matmul(weights_estimated[:, 0], np.transpose(spectra))
    res = data_fitted - data_input[:, 0]

    # R-factor
    assert rfactor.ndim == 1 and len(rfactor) == weights_estimated.shape[1], \
        f"'rfactor' dimensions are incorrect ({rfactor.shape})"
    rf = np.sum(np.abs(res))/np.sum(np.abs(data_input))  # Desired value
    npt.assert_almost_equal(rfactor[0], rf, err_msg="R-factor is computed incorrectly")

    # Residual
    assert residual.ndim == 1 and len(residual) == weights_estimated.shape[1], \
        f"'residual' dimensions are incorrect ({residual.shape})"
    rs = np.sqrt(np.sum(np.square(res)))  # Desired value (this is how 'nnls' computes the residual)
    npt.assert_almost_equal(rfactor[0], rs, err_msg="Residual is computed incorrectly")


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (8,)},
])
def test_fitting_nnls_arguments(dataset_params):
    r"""
    Test _fit_nnls for different values of the parameter 'maxiter' (maximum number of iterations)
    """

    fitting_data = DataForFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # Try running with 'maxiter' argument
    _fitting_nnls(data_input, spectra, maxiter = 10)  # Valid call
    with pytest.raises(AssertionError, match="'maxiter' is zero or negative"):
        _fitting_nnls(data_input, spectra, maxiter = 0)
    with pytest.raises(AssertionError, match="'maxiter' is zero or negative"):
        _fitting_nnls(data_input, spectra, maxiter = -5)


def test_fitting_nnls_fail():
    r"""
    Test _fit_nnls for supported cases of failure
    """
    n_pts, n_refs, n_pixels = 10, 3, 5

    spectra = np.zeros(shape=[n_pts])  # 1D instead of 2D
    data_input = np.zeros(shape=[n_pts, n_refs])
    with pytest.raises(AssertionError, match="Data array 'data' must have 2 dimensions"):
        _fitting_nnls(spectra, data_input)

    spectra = np.zeros(shape=[n_pts, n_pixels])
    data_input = np.zeros(shape=[n_pts])  # 1D instead of 2D
    with pytest.raises(AssertionError, match="Data array 'ref_spectra' must have 2 dimensions"):
        _fitting_nnls(spectra, data_input)

    spectra = np.zeros(shape=[n_pts - 1, n_pixels])  # Wrong number of data points
    data_input = np.zeros(shape=[n_pts, n_refs])
    with pytest.raises(AssertionError, match="number of spectrum points in data .+ do not match"):
        _fitting_nnls(spectra, data_input)


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (8,)},
    {"n_data_dimensions": (15,)},
])
def test_fitting_admm(dataset_params):

    fitting_data = DataForFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # -------------- Test regular fitting ---------------
    weights_estimated, rfactor, convergence, feasibility = \
        _fitting_admm(data_input, spectra)

    fitting_data.validate_output_weights(weights_estimated, decimal=10)

    # Validate 'rfactor' (do it for a single point)
    data_fitted = np.matmul(weights_estimated[:, 0], np.transpose(spectra))
    res = data_fitted - data_input[:, 0]
    assert rfactor.ndim == 1 and len(rfactor) == weights_estimated.shape[1], \
        f"'rfactor' dimensions are incorrect ({rfactor.shape})"
    rf = np.sum(np.abs(res))/np.sum(np.abs(data_input))  # Desired value
    npt.assert_almost_equal(rfactor[0], rf, err_msg="R-factor is computed incorrectly")

    # Check the convergence data
    assert (convergence.ndim == 1) and (convergence.size >= 1) \
           and convergence[-1] < 1e-20, \
           "Convergence array has incorrect dimensions or the alogrithm did not converge"

    # Check feasibility array dimensions
    assert (feasibility.ndim == 1) and (feasibility.size >= 1), \
        "Feasibility array has incorrect dimensions"


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (8,)},
])
def test_fitting_admm_arguments(dataset_params):
    r"""
    Test _fit_nnls for different values of the parameter 'maxiter' (maximum number of iterations)
    """
    fitting_data = DataForFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # Argument 'maxiter'
    _fitting_admm(data_input, spectra, maxiter = 10)  # Valid call
    with pytest.raises(AssertionError, match="'maxiter' is zero or negative"):
        _fitting_admm(data_input, spectra, maxiter = 0)
    with pytest.raises(AssertionError, match="'maxiter' is zero or negative"):
        _fitting_admm(data_input, spectra, maxiter = -5)

    # Argument 'rate'
    _fitting_admm(data_input, spectra, rate = 0.2)  # Valid call
    with pytest.raises(AssertionError, match="'rate' is zero or negative"):
        _fitting_admm(data_input, spectra, rate = 0)
    with pytest.raises(AssertionError, match="'rate' is zero or negative"):
        _fitting_admm(data_input, spectra, rate = -0.2)

    # Argument 'epsilon'
    _fitting_admm(data_input, spectra, epsilon = 1e-10)  # Valid call
    with pytest.raises(AssertionError, match="'epsilon' is zero or negative"):
        _fitting_admm(data_input, spectra, epsilon = 0)
    with pytest.raises(AssertionError, match="'epsilon' is zero or negative"):
        _fitting_admm(data_input, spectra, epsilon = -1e-10)


def test_fitting_admm_fail():
    r"""
    Test _fit_nnls for supported cases of failure
    """
    n_pts, n_refs, n_pixels = 10, 3, 5

    spectra = np.zeros(shape=[n_pts])  # 1D instead of 2D
    data_input = np.zeros(shape=[n_pts, n_refs])
    with pytest.raises(AssertionError, match="Data array 'data' must have 2 dimensions"):
        _fitting_admm(spectra, data_input)

    spectra = np.zeros(shape=[n_pts, n_pixels])
    data_input = np.zeros(shape=[n_pts])  # 1D instead of 2D
    with pytest.raises(AssertionError, match="Data array 'ref_spectra' must have 2 dimensions"):
        _fitting_admm(spectra, data_input)

    spectra = np.zeros(shape=[n_pts - 1, n_pixels])  # Wrong number of data points
    data_input = np.zeros(shape=[n_pts, n_refs])
    with pytest.raises(AssertionError, match="number of spectrum points in data .+ do not match"):
        _fitting_admm(spectra, data_input)


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (10,)},
    {"n_data_dimensions": (10,), "axis": 0},
    {"n_data_dimensions": (10,), "axis": 1},
    {"n_data_dimensions": (10,), "axis": -1},
    {"n_data_dimensions": (1,)},
    {"n_data_dimensions": ()},
    {"n_data_dimensions": (3, 8)},
    {"n_data_dimensions": (1, 8)},
    {"n_data_dimensions": (8, 1)},
    {"n_data_dimensions": (3, 8), "axis": 0},
    {"n_data_dimensions": (3, 8), "axis": 1},
    {"n_data_dimensions": (3, 8), "axis": 2},
    {"n_data_dimensions": (3, 8), "axis": -1},
    {"n_data_dimensions": (3, 8), "axis": -2},
    {"n_data_dimensions": (3, 5, 8)},
    {"n_data_dimensions": (1, 5, 8)},
    {"n_data_dimensions": (3, 1, 8)},
    {"n_data_dimensions": (3, 5, 1)},
    {"n_data_dimensions": (3, 5, 8), "axis": 0},
    {"n_data_dimensions": (3, 5, 8), "axis": 1},
    {"n_data_dimensions": (3, 5, 8), "axis": 2},
    {"n_data_dimensions": (3, 5, 8), "axis": 3},
])
@pytest.mark.parametrize("process_params", [
    {},  # The default method is "nnls"
    {"method": "nnls"},
    {"method": "admm"},
])
def test_fitting_spectrum(dataset_params, process_params):

    fitting_data = DataForFittingTest(**dataset_params)

    params = process_params.copy()  # We don't want to create a reference, since we change 'params'

    if 'axis' in dataset_params:
        params['axis'] = dataset_params['axis']

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # -------------- Test regular fitting ---------------
    weights_estimated, rfactor, results_dict = fitting_spectrum(data_input, spectra, **params)

    fitting_data.validate_output_weights(weights_estimated, decimal=10)

    # We don't verify the values of 'rfactor' and 'residual', since they are verified for each
    #   optimization method separately. We verify only the dimensions of the arrays
    data_dim = dataset_params["n_data_dimensions"]
    assert rfactor.shape == data_dim, \
        f"The shape of 'rfactor' array {rfactor.shape} does not match the shape of data {data_dim}"

    if "method" not in params:
        params["method"] = "nnls"  # This is supposed to be the default value

    # The rest of the checks are individual for optimization method
    if params["method"] == "admm":
        # Check for existance and dimensions of 'convergence' and 'feasibility' arrays
        assert results_dict["method"] == "admm", f"Incorrect method '{results_dict['method']}' "\
                                                 "is reported by ADMM optimization function"
        assert "convergence" in results_dict, \
            "Array 'convergence' is not in the dictionary of results for ADMM optimization method"
        assert "feasibility" in results_dict, \
            "Array 'feasibility' is not in the dictionary of results for ADMM optimization method"
        assert results_dict["convergence"].ndim == 1, \
            "The returned 'convergence' must be 1D array (ADMM optimization method)"
        assert results_dict["feasibility"].ndim == 1, \
            "The returned 'feasibility' must be 1D array (ADMM optimization method)"
        assert results_dict["convergence"].shape == results_dict["feasibility"].shape, \
            "The returned 'convergence' and 'feasibility' arrays must have the same size "\
            "(ADMM optimization method)"
    elif params["method"] == "nnls":
        assert results_dict["method"] == "nnls", f"Incorrect method '{results_dict['method']}' "\
                                                 "is reported by NNLS optimization function"
        assert "residual" in results_dict, \
            "Array 'residual' is not in the dictionary of results for NNLS optimization method"
        assert results_dict['residual'].shape == data_dim, \
            f"The shape of 'residual' array {results_dict['residual'].shape} does not match "\
            f"the shape of data {data_dim}"
    else:
        assert False, f"Unknown optimization method '{params['method']}'"


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (8, 6)},
])
def test_fitting_spectrum_arguments(dataset_params):
    r"""
    Test _fit_nnls for different values of the parameter 'maxiter' (maximum number of iterations)
    """
    fitting_data = DataForFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # Argument 'maxiter'
    fitting_spectrum(data_input, spectra, maxiter = 10)  # Valid call
    with pytest.raises(AssertionError, match="'maxiter' is zero or negative"):
        fitting_spectrum(data_input, spectra, maxiter = 0)
    with pytest.raises(AssertionError, match="'maxiter' is zero or negative"):
        fitting_spectrum(data_input, spectra, maxiter = -5)

    # Argument 'rate'
    fitting_spectrum(data_input, spectra, rate = 0.2)  # Valid call
    with pytest.raises(AssertionError, match="'rate' is zero or negative"):
        fitting_spectrum(data_input, spectra, rate = 0)
    with pytest.raises(AssertionError, match="'rate' is zero or negative"):
        fitting_spectrum(data_input, spectra, rate = -0.2)

    # Argument 'epsilon'
    fitting_spectrum(data_input, spectra, epsilon = 1e-10)  # Valid call
    with pytest.raises(AssertionError, match="'epsilon' is zero or negative"):
        fitting_spectrum(data_input, spectra, epsilon = 0)
    with pytest.raises(AssertionError, match="'epsilon' is zero or negative"):
        fitting_spectrum(data_input, spectra, epsilon = -1e-10)

    # Argument 'method'
    with pytest.raises(AssertionError, match="Fitting method .+ is not supported"):
        fitting_spectrum(data_input, spectra, method = "abc")  # Arbitrary string

    # Argument 'axis'
    with pytest.raises(AssertionError, match="Specified axis .+ does not exist in data array"):
        fitting_spectrum(data_input, spectra, axis = 3)  # Outside the range
    with pytest.raises(AssertionError, match="Specified axis .+ does not exist in data array"):
        fitting_spectrum(data_input, spectra, axis = -4)  # Outside the range


def test_fitting_spectrum_fail():
    r"""
    Test _fit_nnls for supported cases of failure
    """
    n_pts, n_refs, n_pixels = 10, 3, 5

    spectra = np.zeros(shape=[n_pts - 1, n_pixels])  # Wrong number of data points
    data_input = np.zeros(shape=[n_pts, n_refs])
    with pytest.raises(AssertionError, match="number of spectrum points in data .+ do not match"):
        fitting_spectrum(spectra, data_input)



"""
@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (8,)},
    {"n_data_dimensions": (9,)},
    {"n_data_dimensions": (1,)},
    {"n_data_dimensions": (3, 8)},
    {"n_data_dimensions": (4, 7)},
    {"n_data_dimensions": (1, 8)},
    {"n_data_dimensions": (8, 1)},
    {"n_data_dimensions": ()},
])
def test_admm_normal_use(dataset_params):

    fitting_data = DataForAdmmFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # -------------- Test regular fitting ---------------
    weights_estimated, convergence, feasibility = fitting_admm(data_input, spectra)

    fitting_data.validate_output_weights(weights_estimated, decimal=10)

    # Check the convergence data
    assert (convergence.ndim == 1) and (convergence.size >= 1) \
           and convergence[-1] < 1e-20, \
           "Convergence array has incorrect dimensions or the alogrithm did not converge"

    # Check feasibility array dimensions
    assert (feasibility.ndim == 1) and (feasibility.size >= 1), \
        "Feasibility array has incorrect dimensions"


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (3, 8)},
])
def test_admm_try_wrong_input_dimensions(dataset_params):

    fitting_data = DataForAdmmFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # -------------- Try feeding input data with wrong dimensions ----------------
    # Remove one data point (along axis 0)
    data_input_wrong_dimensions = np.delete(data_input, -1, axis=0)
    with pytest.raises(AssertionError,
                       match=r"number of spectrum points in data \(\d+\) " \
                             r"and references \(\d+\) do not match"):
        fitting_admm(data_input_wrong_dimensions, spectra)


@pytest.mark.parametrize("dataset_params", [
    {"n_data_dimensions": (3, 8)},
])
def test_admm_try_wrong_fitting_param_value(dataset_params):

    fitting_data = DataForAdmmFittingTest(**dataset_params)

    spectra = fitting_data.spectra
    data_input = fitting_data.data_input

    # -------------- Set 'rate' to 0.0 ----------------
    with pytest.raises(AssertionError,
                       match=r"parameter 'rate' is zero or negative"):
        fitting_admm(data_input, spectra, rate=0.0)

    # -------------- Set 'maxiter' to 0 ----------------
    with pytest.raises(AssertionError,
                       match=r"parameter 'maxiter' is zero or negative"):
        fitting_admm(data_input, spectra, maxiter=0)

    # -------------- Set 'epsilon' to 0.0 ----------------
    with pytest.raises(AssertionError,
                       match=r"parameter 'epsilon' is zero or negative"):
        fitting_admm(data_input, spectra, epsilon=0.0)
"""