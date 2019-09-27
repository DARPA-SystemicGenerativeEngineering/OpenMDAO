import unittest

import numpy as np
import openmdao.api as om
from openmdao.visualization.meta_model_viewer.meta_model_visualization import MetaModelVisualization


class StructuredMetaModelCompTests(unittest.TestCase):

    def test_working_scipy_slinear(self):

        # Create regular grid interpolator instance
        xor_interp = om.MetaModelStructuredComp(method='scipy_slinear')

        # set up inputs and outputs
        xor_interp.add_input('x', 0.0, training_data=np.array([0.0, 1.0]), units=None)
        xor_interp.add_input('y', 1.0, training_data=np.array([0.0, 1.0]), units=None)

        xor_interp.add_output(
            'xor', 1.0, training_data=np.array([[0.0, 1.0], [1.0, 0.0]]), units=None)

        # Set up the OpenMDAO model
        model = om.Group()
        ivc = om.IndepVarComp()
        ivc.add_output('x', 0.0)
        ivc.add_output('y', 1.0)
        model.add_subsystem('ivc', ivc, promotes=["*"])
        model.add_subsystem('comp', xor_interp, promotes=["*"])
        prob = om.Problem(model)
        prob.setup()

        MetaModelVisualization(xor_interp)

    def test_working_slinear(self):

        num_train = 10

        x0_min, x0_max = -5.0, 10.0
        x1_min, x1_max = 0.0, 15.0
        train_x0 = np.linspace(x0_min, x0_max, num_train)
        train_x1 = np.linspace(x1_min, x1_max, num_train)
        t_data = np.array([[308.12909601, 253.61567418, 204.6578079, 161.25549718, 123.40874201, 91.1175424,   64.38189835,  43.20180985,  27.5772769,   17.50829952],
                        [162.89542418, 123.20470795,  89.06954726,  60.48994214,  37.46589257, 19.99739855,   8.08446009,   1.72707719,   0.92524984,   5.67897804,],
                        [ 90.2866907,   63.02637433,  41.32161352,  25.17240826,  14.57875856, 9.54066442,  10.05812583,  16.13114279,  27.75971531,  44.94384339,],
                        [ 55.60211264,  38.37989042,  26.71322375,  20.60211264,  20.04655709, 25.04655709,  35.60211264,  51.71322375,  73.37989042, 100.60211264],
                        [ 22.81724065,  13.24080685,   9.2199286,   10.75460591,  17.84483877, 30.49062719, 48.69197117,  72.4488707,  101.76132579, 136.62933643],
                        [  5.11168719,   0.78873608,   2.02134053,   8.80950054,  21.1532161, 39.05248721,  62.50731389,  91.51769611, 126.0836339,  166.20512723],
                        [ 14.3413983,   12.87962416,  16.97340558,  26.62274256,  41.82763509, 62.58808317,  88.90408682, 120.77564601, 158.20276077, 201.18543108],
                        [ 20.18431209,  19.1914092,   23.75406186,  33.87227009,  49.54603386, 70.77535319,  97.56022808, 129.90065853, 167.79664453, 211.24818608],
                        [  8.48953212,   5.57319475,   8.21241294,  16.40718668,  30.15751598, 49.46340083,  74.32484124, 104.74183721, 140.71438873, 182.2424958 ],
                        [ 10.96088904,   3.72881146,   2.05228945,   5.93132298,  15.36591208, 30.35605673,  50.90175693,  77.00301269, 108.65982401, 145.87219088]])

        prob = om.Problem()
        ivc = om.IndepVarComp()
        ivc.add_output('x0', 0.0)
        ivc.add_output('x1', 0.0)

        prob.model.add_subsystem('p', ivc, promotes=['*'])
        mm = prob.model.add_subsystem('mm', om.MetaModelStructuredComp(method='slinear'),
                                    promotes=['x0', 'x1'])
        mm.add_input('x0', 0.0, train_x0)
        mm.add_input('x1', 0.0, train_x1)
        mm.add_output('f', 0.0, t_data)

        prob.setup()
        prob.final_setup()

        MetaModelVisualization(mm)


    def test_working_scipy_cubic(self):

        # create input param training data, of sizes 25, 5, and 10 points resp.
        p1 = np.linspace(0, 100, 25)
        p2 = np.linspace(-10, 10, 5)
        p3 = np.linspace(0, 1, 10)

        # can use meshgrid to create a 3D array of test data
        P1, P2, P3 = np.meshgrid(p1, p2, p3, indexing='ij')
        f = np.sqrt(P1) + P2 * P3

        # Create regular grid interpolator instance
        interp = om.MetaModelStructuredComp(method='scipy_cubic')
        interp.add_input('p1', 0.5, training_data=p1)
        interp.add_input('p2', 0.0, training_data=p2)
        interp.add_input('p3', 3.14, training_data=p3)

        interp.add_output('f', 0.0, training_data=f)

        # Set up the OpenMDAO model
        model = om.Group()
        model.add_subsystem('comp', interp, promotes=["*"])
        prob = om.Problem(model)
        prob.setup()

        MetaModelVisualization(interp)

    def test_working_cubic(self):

        # create input param training data, of sizes 25, 5, and 10 points resp.
        p1 = np.linspace(0, 100, 25)
        p2 = np.linspace(-10, 10, 5)
        p3 = np.linspace(0, 1, 10)

        # can use meshgrid to create a 3D array of test data
        P1, P2, P3 = np.meshgrid(p1, p2, p3, indexing='ij')
        f = np.sqrt(P1) + P2 * P3

        # Create regular grid interpolator instance
        interp = om.MetaModelStructuredComp(method='cubic')
        interp.add_input('p1', 0.5, training_data=p1)
        interp.add_input('p2', 0.0, training_data=p2)
        interp.add_input('p3', 3.14, training_data=p3)

        interp.add_output('f', 0.0, training_data=f)

        # Set up the OpenMDAO model
        model = om.Group()
        model.add_subsystem('comp', interp, promotes=["*"])
        prob = om.Problem(model)
        prob.setup()

        MetaModelVisualization(interp)

    def test_working_multipoint_scipy_cubic(self):

        # create input param training data, of sizes 25, 5, and 10 points resp.
        p1 = np.linspace(0, 100, 25)
        p2 = np.linspace(-10, 10, 5)
        p3 = np.linspace(0, 1, 10)

        # can use meshgrid to create a 3D array of test data
        P1, P2, P3 = np.meshgrid(p1, p2, p3, indexing='ij')
        f = np.sqrt(P1) + P2 * P3

        # Create regular grid interpolator instance
        interp = om.MetaModelStructuredComp(method='scipy_cubic', vec_size=2)
        interp.add_input('p1', 0.5, training_data=p1)
        interp.add_input('p2', 0.0, training_data=p2)
        interp.add_input('p3', 3.14, training_data=p3)

        interp.add_output('f', 0.0, training_data=f)

        # Set up the OpenMDAO model
        model = om.Group()
        model.add_subsystem('comp', interp, promotes=["*"])
        prob = om.Problem(model)
        prob.setup()

        MetaModelVisualization(interp)



if __name__ == '__main__':
    unittest.main()