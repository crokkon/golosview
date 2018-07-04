#!/usr/bin/python
from flask import Flask, render_template, request
from beem.utils import construct_authorperm
import traceback

from gvaccount import GVAccount, GVComment
from opviewer import format_op, format_comment_options, format_active_votes

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/<username>')
def profile(username : str):
    error = ""
    optable = ""
    acc_info = {}

    if username.startswith("@"):
        username = username[1:]

    if len(username) < 3 or len(username) > 16:
        error = "Invalid username"
        return render_template("profile.html", error=error,
                               account=acc_info, optable=optable)

    # get account information from the blockchain
    try:
        account = GVAccount(username)
    except:
        error = traceback.format_exc()
        return render_template("profile.html", error=error,
                               account=acc_info, optable=optable)

    page = request.args.get('page', default = 1, type = int)
    if page < 1 or page > account.pages:
        error = "Invalid page number"
        return render_template("profile.html", error=error,
                               account=acc_info, optable=optable)

    # preprocess general account information for integration in template
    acc_info = account.parse()

    # get the account operations history from the blockchain
    try:
        operations = account.operations(page)
    except:
        error = traceback.format_exc()
        return render_template("profile.html", error=error,
                               account=acc_info, optable=optable)

    # build HTML for list of operations
    for op in operations:
        optable += format_op(op, own=username)

    return render_template("profile.html", error=error,
                           account=acc_info, optable=optable,
                           total_pages=account.pages, page=page)


@app.route('/<username>/<permlink>', defaults={'category': None})
@app.route('/<category>/<username>/<permlink>')
def comment(category : str, username : str, permlink : str):
    error = ""
    comment_info = {}
    if username.startswith("@"):
        username = username[1:]

    try:
        identifier = construct_authorperm(username, permlink)
        com = GVComment(identifier)
    except:
        error = traceback.format_exc()
        return render_template("comment.html", error=error,
                               comment=comment_info)

    # preprocess comment data for integration in template
    comment_info = com.parse()
    comment_options = format_comment_options(comment_info)
    comment_votes = format_active_votes(comment_info)

    return render_template("comment.html", error=error,
                           comment=comment_info,
                           comment_options=comment_options,
                           comment_votes=comment_votes)


if __name__ == '__main__':
    app.run(debug=config.DEBUG, use_reloader=True)
