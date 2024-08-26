# Join our discord

[AI Master](https://discord.gg/wetGqcgxDR)

# Canvas Schedule Helper

This Python script calculates the total duration of all videos in a course hosted on the Canvas Learning Management System. It is designed to help students plan their study time more efficiently by giving them an idea of how long it will take to go through course materials.

## Example output

![Example output](example-output.png)

## Usage

### Prerequisites

- Python 3

### Installation

1. **Clone the Repository**: First, clone this repository to your local machine using git:

   ```bash
   git clone https://github.com/daringcalf/canvas-schedule-helper.git
   ```

2. **Install Dependencies**: Inside the cloned directory, install the required Python packages:

   ```bash
   cd canvas-schedule-helper
   ```

   #### Here you can choose venv or pipenv or any others you prefer.

   ##### activate virtual environment for venv and install:

   ```
   python3 -m venv venv
   source venv/bin/activate

   pip install -r requirements.txt
   ```

   ##### activate virtual environment for pipenv and install:

   ```
   pipenv shell

   pipenv install
   ```

### Running the Script

To use this script, you must provide the course id and the cookies from your browser.

1. **Obtain Cookies**: Navigate to your Canvas course page in your web browser. You'll need to retrieve your session cookies.
   ![Chrome Cookies Guide](chrome-cookies.jpg)

2. **Execute the Script**: Run the script and provide the CourseId and cookies when prompted. The `<CourseId>` is the number in the course URL. For example, if the course URL is `https://canvas.asu.edu/courses/181496/modules`, then the `<CourseId>` is 181496.

   ```bash
   python main.py
   # The script will prompt you to enter:
   Enter course ID: <CourseId>
   Enter cookies: <paste Cookies here>
   ```

## Contributing

Feel free to dive in! [Open an issue](https://https://github.com/daringcalf/canvas-schedule-helper/issues/new) or submit PRs.

### Steps to Contribute

- Fork the repo on GitHub
- Clone this project to your own machine
- Commit changes to your own branch
- Push your work back up to your fork
- Submit a Pull request so that your changes can be reviewed

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgments

This tool was created to help students manage their study time more effectively. If you find it helpful, please consider giving it a star. Your support means a lot!
