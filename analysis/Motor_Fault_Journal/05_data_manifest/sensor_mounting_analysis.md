# ADXL335 Mounting and Axis Analysis

## Photograph

The ADXL335 breakout board is bonded directly to the motor housing near the front/drive-end bearing. This is a housing-vibration measurement, not a shaft-mounted measurement. The board is approximately tangent to the upper housing surface.

## Static-data check

The archived stationary vibration data have representative values close to X = -0.07 g, Y = 0.05 g, and Z = -1.00 g. Gravity therefore appears almost entirely on Z, while X and Y remain near zero.

This supports the following physical interpretation:

- Z: approximately vertical/radial, normal to the sensor PCB and aligned with gravity.
- X and Y: two orthogonal directions approximately parallel to the PCB and horizontal.

The image suggests one in-plane direction follows the motor/shaft axis and the other is transverse to it. However, the silkscreen and camera perspective are not clear enough to assign axial versus transverse to X and Y with publication-level certainty.

## Archived placement note

`adxl335 placement.docx` states that X, Y, and Z represent a front sensor placement, while X1, Y1, and Z1 represent a back-of-motor placement. This confirms that the photographed board is one of the housing locations considered in the experiment, but it does not define the axis arrows.

## Manuscript-safe description

“A three-axis ADXL335 accelerometer was bonded to the motor housing near the drive-end bearing. The Z axis was approximately vertical/radial, as confirmed by its approximately -1 g stationary offset, while X and Y represented orthogonal in-plane housing-vibration directions.”

