#!/usr/bin/python
import config
from beem.utils import construct_authorperm, reputation_to_score
from flask import render_template
import json
import pprint

def vote_action(weight):
    if weight > 0:
        return "upvotes"
    elif weight == 0:
        return "unvotes"
    else:
        return "downvotes"


def format_permlink(args):
    if type(args) == dict and 'comment_author' in args and \
       'comment_permlink' in args:
        args['author'] = args['comment_author']
        args['permlink'] = args['comment_permlink']
    authorperm = construct_authorperm(args)
    return '<a href="/%s">%s</a>' % (authorperm, authorperm)


def format_authorlink(username, own_username=None):
    if username == own_username:
        return '<b>%s</b>' % (username)
    else:
        return '<a href="/@%s">%s</a>' % (username, username)


def get_rewards(op):
    """return all reward fields contained in a blockchain operation as a
    single string

    """
    rewards = []
    for reward_type in ['reward', 'steem_payout', 'sbd_payout',
                        'vesting_payout']:
        if reward_type in op:
            rewards.append(op[reward_type])
    return ", ".join(rewards)


def format_op(op, own=None):
    """create a HTML representation of a blockchain operation using the
    template in templates/op.html

    """
    timestamp = op['timestamp']
    block = op['block']
    tp = op['type']
    index = op['index']

    # default for unsupported operations and fallback for parsing
    # errors: strip irrelevant parts of the raw op data and show the
    # remaining fields as text
    for optype in ['block', 'op_in_trx', 'required_auths', 'trx',
                   'trx_id', 'required_posting_auths', 'index',
                   'virtual_op', 'trx_in_block', '_id', 'owner',
                   'active', 'posting', 'memo_key', 'timestamp']:
        if optype in op:
            del op[optype]
    opstr = "<code><pre>%s</pre></code>" % (json.dumps(op, indent=2))

    # handle supported operation types
    if tp == "vote":
        weight = int(op['weight']) / 100
        opstr = "%s %s %s (%.2f%%)" % \
                (format_authorlink(op['voter'], own),
                 vote_action(weight), format_permlink(op), weight)
    elif tp == "transfer_to_vesting":
        opstr = "%s vests %s to %s" % \
                (format_authorlink(op['from'], own), op['amount'],
                 format_authorlink(op['to'], own))

    elif tp == "transfer":
        opstr = "%s transfers %s to %s: <code>%s</code>" % \
                (format_authorlink(op['from'], own), op['amount'],
                 format_authorlink(op['to'], own), op['memo'])

    elif tp == "curation_reward":
        opstr = "Curation reward: %s for %s" % (get_rewards(op),
                                                format_permlink(op))
    elif tp == "author_reward":
        opstr = "Author reward: %s for %s" % (get_rewards(op),
                                              format_permlink(op))
    elif tp == "comment_benefactor_reward":
        opstr = "Benefactor reward for %s: %s for %s" % \
                (format_authorlink(op['benefactor']), get_rewards(op),
                 format_permlink(op))

    elif tp == "account_create":
        opstr = "%s creates account %s (fee: %s)" % \
                (format_authorlink(op['creator']),
                 format_authorlink(op['new_account_name']), op['fee'])

    elif tp == "account_witness_vote":
        if op['approve']:
            action = "votes for "
        else:
            action = "unvotes for "
        opstr = "%s %s %s as witness" % \
                (format_authorlink(op['account'], own), action,
                 format_authorlink(op['witness'], own))

    elif tp == "fill_vesting_withdraw":
        opstr = "%s withdraws %s as %s to %s" % \
                (format_authorlink(op['from_account'], own),
                 op['withdrawn'], op['deposited'],
                 format_authorlink(op['to_account'], own))

    elif tp == "comment":
        if op['parent_author']:
            optype = "replies to"
            link = {'author': op['parent_author'], 'permlink': op['parent_permlink']}
        else:
            optype = "authors a post:"
            link = {'author': op['author'], 'permlink': op['permlink']}

        opstr = "%s %s %s" % (format_authorlink(op['author'], own),
                              optype, format_permlink(link))

    elif tp == "comment_options":
        opstr = "Comment options for %s: " % (format_permlink(op))
        ops = []
        for key in ['max_accepted_payout', 'allow_curation_rewards',
                    'allow_votes', 'percent_steem_dollars']:
            if key in op:
                ops.append("%s: %s" % (key, op[key]))
        opstr += "<pre>" + "\n".join(ops) + "</pre>"

    elif tp == "custom_json":
        try:
            jsondata = json.loads(op['json'])
        except:
            jsondata = str(op['json'])

        if len(jsondata) == 2:
            optype = jsondata[0]
            opdict = jsondata[1]
            if optype == "follow" and 'what' in opdict and \
               'blog' in opdict['what'] and 'follower' in opdict \
               and 'following' in opdict:
                opstr = "%s follows %s" % \
                (format_authorlink(opdict['follower'], own),
                 format_authorlink(opdict['following'], own))
            if optype == "follow" and 'what' in opdict and \
               "" in opdict['what'] and 'follower' in opdict \
               and 'following' in opdict:
                opstr = "%s unfollows %s" % \
                (format_authorlink(opdict['follower'], own),
                 format_authorlink(opdict['following'], own))
            if optype == "reblog" and 'author' in opdict and \
               'permlink' in opdict:
                opstr = "%s rebloggs %s" % \
                        (format_authorlink(opdict['account'], own),
                         format_permlink(opdict))

    return render_template("op.html", timestamp=timestamp,
                           block=block, opstr=opstr, id=index)


def format_comment_options(comment):
    exclude_keys = ['author', 'permlink', 'active_votes', 'url',
                    'body_length', 'body', 'replies', 'authorperm',
                    'payout']
    commentstr = ""
    for key in sorted(comment.keys()):
        if key in exclude_keys:
            continue
        val = comment[key]

        code = False
        if key in ['json_metadata', 'beneficiaries']:
            code = True
            val = pprint.pformat(val)

        if type(val) == list:
            val = ", ".join(val)

        commentstr += render_template("row.html", cols=[key, val],
                                      code=code)
    return commentstr


def format_active_votes(comment):
    keys = ['time', 'voter', 'percent', 'rshares', 'weight',
            'reputation']
    labels = [k.capitalize() for k in keys]
    votestr = render_template("table_header.html", cols=labels)
    for vote in sorted(comment['active_votes'], key=lambda k:
                       k['time']):
        entries = [vote[k] for k in keys]
        votestr += render_template("row.html", cols=entries)
    return votestr
