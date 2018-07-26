# pygbr
Abstracts creation of gerber files for use in electronic design automation. Part of a larger Python-based EDA framework in progress.

Improved documentation to come. Currently all basic gerber concepts (apertures, graphic objects, layers, etc) are captured in Python data structures and manipulated in ways intended to be intuitive and true to how gerber files are constructed.

As a proof-of-concept of parameterized layout generation, I've fabricated a PCB using a script which creates multiple instances of a simple arbitrary design with varying parameters. See examples/ for the code and resulting gerber files.
