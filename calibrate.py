import logging
import cv2
import numpy as np
logging.getLogger("calibrator")


def draw_matches_opencv(img1, kp1, img2, kp2, matches):
    """
    Source: http://stackoverflow.com/questions/20259025/module-object-has-no-attribute-drawmatches-opencv-python
    This function takes in two images with their associated
    keypoints, as well as a list of DMatch data structure (matches)
    that contains which keypoints matched in which images.

    An image will be produced where a montage is shown with the first image followed
    by the second image beside it.

    Keypoints are delineated with circles, while lines are connected between
    matching keypoints.

    :param img1: grayscale image
    :type img1: np.ndarray
    :param kp1: Detected list of keypoints through any of the OpenCV keypoint detection algorithms
    :type kp1: list
    :param img2: grayscale image
    :type img2: np.ndarray
    :param kp2: Detected list of keypoints through any of the OpenCV keypoint detection algorithms
    :type kp2: list
    :param matches: A list of matches of corresponding keypoints through any OpenCV keypoint matching algorithm
    :type matches: list
    :return: image of matches between images.
    :rtype: np.ndarray
    """
    # define a taget height
    TARGETHEIGHT = 800

    # Create a new output image that concatenates the two images together
    # (a.k.a) a montage
    rows1 = img1.shape[0]
    cols1 = img1.shape[1]
    rows2 = img2.shape[0]
    cols2 = img2.shape[1]

    out = np.zeros((max([rows1, rows2]), cols1 + cols2, 3), dtype='uint8')


    # Place the first image to the left
    out[:rows1, :cols1, :] = np.dstack([img1, img1, img1])

    # Place the next image to the right of it
    out[:rows2, cols1:cols1 + cols2, :] = np.dstack([img2, img2, img2])
    ar = out.shape[1] / out.shape[0]
    w = int(TARGETHEIGHT * ar)
    # For each pair of points we have between both images
    # draw circles, then connect a line between them
    for mat in matches:
        # Get the matching keypoints for each of the images
        img1_idx = mat.queryIdx
        img2_idx = mat.trainIdx

        # x - columns
        # y - rows
        (x1, y1) = kp1[img1_idx].pt
        (x2, y2) = kp2[img2_idx].pt

        # Draw a small circle at both co-ordinates
        # radius 4
        # colour blue
        # thickness = 1
        cv2.circle(out, (int(x1), int(y1)), 4, (255, 0, 0), 1)
        cv2.circle(out, (int(x2) + cols1, int(y2)), 4, (255, 0, 0), 1)

        # Draw a line in between the two points
        # thickness = 3
        # colour red green blue
        cv2.line(out, (int(x1), int(y1)), (int(x2) + cols1, int(y2)),
                 (0, 0, 255), max(int(out.shape[0] / TARGETHEIGHT), 2))

    # rescale image here.

    out = cv2.resize(out, (w, TARGETHEIGHT))
    return out


def get_displacement_opencv(image0, image1):
    """
    Gets displacement (in pixels I think) difference between 2 images using opencv

    :param image0: reference image
    :type image0: np.ndarray
    :param image1: target image
    :type image1: np.ndarray
    :return:
    """
    import cv2

    img1 = cv2.cvtColor(image0, cv2.COLOR_BGR2GRAY)
    img2 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)

    # Create ORB detector with 1000 keypoints with a scaling pyramid factor of 1.2
    # gareth changed here from cv2.ORB to cv2.ORB_create for opencv3.1.0 compatibility.
    orb = cv2.ORB_create(1000, 1.2)

    # Detect keypoints
    (kp1, des1) = orb.detectAndCompute(img1, None)
    (kp2, des2) = orb.detectAndCompute(img2, None)

    # Create matcher and do matching
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    # Sort the matches based on distance.  Least distance
    # is better
    matches = sorted(matches, key=lambda val: val.distance)

    # collect displacement from the first 10 matches
    dx_list = []
    dy_list = []
    for mat in matches[:20]:
        # Get the matching keypoints for each of the images
        img1_idx = mat.queryIdx
        img2_idx = mat.trainIdx

        # x - columns
        # y - rows
        (x1, y1) = kp1[img1_idx].pt
        (x2, y2) = kp2[img2_idx].pt
        dx_list.append(abs(x1 - x2))
        dy_list.append(abs(y1 - y2))

    dx_median = np.median(np.asarray(dx_list, dtype=np.double))
    dy_median = np.median(np.asarray(dy_list, dtype=np.double))

    img3 = draw_matches_opencv(img1, kp1, img2, kp2, matches[:20])
    cv2.imwrite("matches.jpg", img3)
    del img1
    del img2
    return dx_median, dy_median


def get_displacement(image0, image1):
    """
    Gets displacement (in pixels I think) difference between 2 images using scikit-image
    not as accurate as the opencv version i think.

    :param image0: reference image
    :param image1: target image
    :return:
    """
    from skimage.feature import (match_descriptors, ORB, plot_matches)
    from skimage.color import rgb2gray
    from scipy.spatial.distance import hamming
    from scipy import misc
    image0_gray = rgb2gray(image0)
    image1_gray = rgb2gray(image1)
    descriptor_extractor = ORB(n_keypoints=200)

    descriptor_extractor.detect_and_extract(image0_gray)
    keypoints1 = descriptor_extractor.keypoints
    descriptors1 = descriptor_extractor.descriptors

    descriptor_extractor.detect_and_extract(image1_gray)
    keypoints2 = descriptor_extractor.keypoints
    descriptors2 = descriptor_extractor.descriptors

    matches12 = match_descriptors(descriptors1, descriptors2, cross_check=True)

    # Sort the matches based on distance.  Least distance
    # is better
    distances12 = []
    for match in matches12:
        distance = hamming(descriptors1[match[0]], descriptors2[match[1]])
        distances12.append(distance)

    indices = np.arange(len(matches12))
    indices = [index for (_, index) in sorted(zip(distances12, indices))]
    matches12 = matches12[indices]

    # collect displacement from the first 10 matches
    dx_list = []
    dy_list = []
    for mat in matches12[:10]:
        # Get the matching key points for each of the images
        img1_idx = mat[0]
        img2_idx = mat[1]

        # x - columns
        # y - rows
        (x1, y1) = keypoints1[img1_idx]
        (x2, y2) = keypoints2[img2_idx]
        dx_list.append(abs(x1 - x2))
        dy_list.append(abs(y1 - y2))

    dx_median = np.median(np.asarray(dx_list, dtype=np.double))
    dy_median = np.median(np.asarray(dy_list, dtype=np.double))
    # plot_matches(image0, image1, descriptors1, descriptors2, matches12[:10])
    return dx_median, dy_median



def format_calibration(fovlists: tuple, test: str) -> str:
    """
    formats a list of calibrated tuple of lists of fields of view and gives some statistics
    about the measurements.

    :param fovlists: 2 length tuple of lists of hfov and vfov - tuple(list(hfov), list(vfov))
    :type fovlists: tuple[ list(float), list(float) ]
    :param test: prefix for put before the output (ie, which number test it is)
    :type test: str
    :return: formattted string of the camera calibration.
    :rtype: str
    """
    s = u"\n{test_num}).\n\tHFOV:\n{havg:.2f}±{havar:.4f},\tσ: {hstdev}\n\tVFOV:\n{vavg:.2f}±{vavar:.4f},\tσ: {vstdev:.4f}\n"
    h, v = fovlists
    return s.format(
        test_num=test,
        havg=np.average(h),
        havar=max(h) - min(h),
        hstdev=np.std(h),
        vavg=np.average(v),
        vavar=max(v) - min(v),
        vstdev=np.std(v)
    )


def test_calibration(self, number_of_tests: int):
    """
    Tests the calibration process for accuracy, and prints the output values.

    :param number_of_tests: number of times to calibrate and compare calibration values.
    """
    import random
    self.logger.info("Testing {} times".format(number_of_tests))

    # tests = dict((_, int(random.uniform(1, 4))) for _ in range(number_of_tests))
    def get_unif():
        a = random.uniform(2, 2)
        while abs(a) < 1:
            a = random.uniform(2, 2)
        return a

    tests = {_: 2 for _ in range(number_of_tests)}

    self._pantilt.position = np.mean(self._pantilt.pan_range), 0

    for test, inc in tests.items():
        self.logger.info("Testing with opencv {}".format(test))
        fovlists = self.calibrate_fov_list(increment=inc)
        self.logger.info(self.format_calibration(fovlists, test))
        self._pantilt._position = np.mean(self._pantilt.pan_range), 0
        self.logger.info("Testing without opencv {}".format(test))
        fovlists = self.calibrate_fov_list(increment=inc, use_opencv=False)

        self.logger.info(self.format_calibration(fovlists, test))
    self._pantilt.position = np.mean(self._pantilt.pan_range), 0


def calibrate_fov_list(self,
                       zoom_list: list = range(50, 1000, 100),
                       panpos: float = None,
                       tiltpos: float = None,
                       increment: float = 2,
                       use_opencv: bool = True) -> tuple:
    """
    calibrates the Panorama for a list of zoom levels.

    :param zoom_list: list of zoom positions to calibrate
    :param panpos: pan position to calibrate
    :param tiltpos: tilt ""
    :param increment: pan increment amount for the calibration
    :param use_opencv: whether to use opencv
    :return: 2 length tuple of lists of hfov and vfov - tuple(list(hfov), list(vfov))
    """
    camhfovlist = []
    camvfovlist = []
    self._pantilt.zoom_position = zoom_list[0] - 5
    time.sleep(1)
    curpos = self._pantilt.position
    panpos = panpos or curpos[0]
    tiltpos = tiltpos or curpos[1]
    for idx, zoompos in enumerate(zoom_list):
        self._pantilt._position = np.mean(self._pantilt.pan_range), 0
        self._pantilt.zoom_position = zoompos
        self.logger.info("Calibrating {}/{}".format(idx + 1, len(zoom_list)))
        time.sleep(1)
        hf, vf = self.calibrate_fov(zoompos, panpos, tiltpos, increment, use_opencv=use_opencv)

        if hf and vf:
            camhfovlist.append(hf)
            camvfovlist.append(vf)
    time.sleep(1)
    self._pantilt.position = panpos, tiltpos
    return camhfovlist, camvfovlist


def calibrate_fov(self,
                  zoom_pos: float,
                  pan_pos: float,
                  tilt_pos: float,
                  increment: float,
                  use_opencv: bool = True) -> tuple:
    """
    Capture images at different pan/tilt angles, then measure the pixel
    displacement between the images to estimate the field-of-view angle.

    This function is also designed to reject outliers when measuring.

    :param zoom_pos: begin zoom position
    :type zoom_pos: float
    :param pan_pos: begin pan position
    :type pan_pos: float
    :param tilt_pos: begin tilt position
    :type tilt_pos: float
    :param increment: amount to increment to get displacement.
    :type increment: float
    :param use_opencv: Whether to use opencv or scikit image for displacement algorithm
    :type use_opencv: bool
    :return: tuple of hfov, vfov estimates
    :rtype: tuple[float,float]
    """

    self._pantilt.zoom_position = zoom_pos
    self._camera.capture()
    hestimates = []
    vestimates = []
    # add nearby position to reduce backlash
    self._pantilt.position = (pan_pos, tilt_pos)
    time.sleep(0.2)

    hfov_estimate = vfov_estimate = hfov = vfov = None
    reference_image = displaced_image = None
    reference_position = self._pantilt.position

    while True:
        reference_image = self._camera.capture()
        if reference_image is not None:
            reference_image = reference_image
            break

    def reject_outliers(data, m=2.):
        try:
            d = np.abs(data - np.median(data))
            mdev = np.median(d)
            s = d / mdev if mdev else 0.
            return data[s < m]
        except:
            self.logger.error("Error rejecting outliers")
            return data

    def measure(movement: float) -> tuple:
        movement = (movement, movement)
        displ_image = None
        self._pantilt.position = pan_pos, tilt_pos
        pos = self._pantilt.position

        position = (pos[0] + movement[0], pos[1] + movement[1])

        # print("Measuring at {}|{}".format(*position))
        self._pantilt.position = position
        time.sleep(0.25)
        while True:
            # make sure camera finishes refocusing
            displ_image = self._camera.capture()
            if displ_image is not None:
                break

        if use_opencv:
            dx, dy = get_displacement_opencv(reference_image, displ_image)
        else:
            dx, dy = get_displacement(reference_image, displ_image)

        assert dx != 0 and dy != 0, "Couldn't get displacement"

        dxp = dx / reference_image.shape[1]
        dyp = dy / reference_image.shape[0]
        if dxp > 0.35 or dyp > 0.35:
            return None, None

        ptzpos = self._pantilt.position

        displacement = abs(ptzpos[0] - reference_position[0]), abs(ptzpos[1] - reference_position[1])

        if abs(displacement[0] - movement[0]) > 1.0:
            self.logger.error("Displacement error pan {0:.4f}".format(abs(displacement[0] - movement[0])))
        if abs(displacement[1] - movement[1]) > 1.0:
            self.logger.error("Displacement error tilt {0:.4f}".format(abs(displacement[1] - movement[1])))

        hfovt = reference_image.shape[1] * displacement[0] / dx
        vfovt = reference_image.shape[0] * displacement[1] / dy
        self.logger.debug("Guess: {0:.3f}|{1:.3f}".format(hfovt, vfovt))
        print("Guess: {0:.3f}|{1:.3f}".format(hfovt, vfovt))
        return hfovt, vfovt

    hestimates = []
    vestimates = []

    for a in np.arange(1, 20, 0.25):
        h, v = measure(a * increment)
        if not all((h, v)):
            break
        hestimates.append(h)
        vestimates.append(v)
    else:
        self.logger.error("probably very wrong calibration for some reason")
        return None, None

    lh, lv = len(hestimates), len(vestimates)
    hestimates, vestimates = reject_outliers(np.array(hestimates)), reject_outliers(np.array(vestimates))
    self.logger.info("removed outliers: h{} v{} ".format(lh - len(hestimates), lv - len(vestimates)))
    hfov_estimate, vfov_estimate = np.mean(hestimates), np.mean(vestimates)

    self.logger.info(Panorama.format_calibration((hestimates, vestimates), "This guess: "))

    self._pantilt._position = np.mean(self._pantilt.pan_range), 0
    time.sleep(1)
    return hfov_estimate, vfov_estimate


def quick_calibrate(self, increment: float):
    """
    Performs a quick calibration, a single time, and store the calibration values in the child camera object,
    and the child ptz object.
    :param increment: amount to increment by until we get optimal displacement.
    :type increment: float
    """
    h, v = self.calibrate_fov(self._pantilt._zoom_position, float(np.mean(self._pan_range)),
                              float(np.mean(self._tilt_range)), increment=increment)
    self._pantilt.zoom_list = [0]
    self._camera.vfov_list = [v]
    self._camera.hfov_list = [h]
    self._camera.hfov = h
    self._camera.vfov = v