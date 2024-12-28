from flask import Flask, jsonify, request, url_for, redirect, session,render_template
app = Flask(__name__)

# This is the HTML, normally you would abstract it out into a template file and have Jinja render it
HTML = """

"""

@app.route('/_refresh')                                # 5
def refresh():
    # print(request.args) to see what the Javascript sent to us
    print('DEBUG: Refresh requested')


    # Query your Thingspeak here and then pass the new data back to Javascript below


    # Build our response (a Python "dict") to send back to Javascript
    response =  { 
        'status' : 'Success', 
        'data': "A new line derived from Thingspeak",
    }
    print(f'DEBUG: Sending response {response}')
    return jsonify(response)                          # 6 - send the result to client


@app.route('/')
def main():
    print(f'DEBUG: Sending main page')
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)