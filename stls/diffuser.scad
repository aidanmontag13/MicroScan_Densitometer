columns = 12;
rows = 8;

diameter = 5;
block_height = 1;
spacing_x = 10;
spacing_y = (8/7) * 10;
buffer_x = 10;
buffer_y = 10;

difference() {
    // Solid block
    translate([-buffer_x, -buffer_y, 0])
        cube([
            (columns-1)*spacing_x + 2 * buffer_x,
            (rows-1)*spacing_y + 2 * buffer_y,
            block_height
        ]);

    // Cut cylindrical holes
    for (x = [0:columns-1]) {
        for (y = [0:rows-1]) {
            translate([
                x*spacing_x,
                y*spacing_y,
                -1
            ])
                cylinder(h=block_height+2, d=diameter, $fn=48);
        }
    }
}