"""飞书卡片模板 - 家庭管理交互

提供飞书卡片JSON模板，用于：
1. 创建家庭卡片
2. 添加家庭成员卡片
3. 家庭信息展示卡片
4. 邀请链接分享卡片

飞书卡片格式参考：
https://open.feishu.cn/document/ukTMukTMukTM/uYjNwUjL2YDM14iN2ATN
"""

import json
from typing import Dict, Any


def create_family_card() -> Dict[str, Any]:
    """创建家庭的交互卡片"""
    return {
        "type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🏠 创建家庭组织"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": "欢迎使用家庭管家！创建家庭后可以：\n• 管理家庭库存\n• 邀请家人加入\n• 接收补货提醒"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "input",
                    "name": "family_name",
                    "placeholder": {
                        "tag": "plain_text",
                        "content": "请输入家庭名称（如：幸福之家）"
                    },
                    "required": True
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**初始成员构成**（可选，帮助预测消耗速度）"
                    }
                },
                {
                    "tag": "input",
                    "name": "initial_members",
                    "placeholder": {
                        "tag": "plain_text",
                        "content": "例如：4个大人、1个小孩、2只狗"
                    },
                    "required": False
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "创建家庭"
                            },
                            "type": "primary",
                            "value": {
                                "action": "create_family"
                            }
                        }
                    ]
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "💡 创建后会生成邀请链接，可发送给家人加入"
                        }
                    ]
                }
            ]
        }
    }


def add_family_member_card() -> Dict[str, Any]:
    """添加家庭成员的交互卡片"""
    return {
        "type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "➕ 添加家庭成员"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": "添加家庭成员后，系统会根据成员数量预测消耗速度，提醒更准确！"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "**选择成员类型**"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "select_static",
                            "name": "member_type",
                            "placeholder": {
                                "tag": "plain_text",
                                "content": "请选择"
                            },
                            "options": [
                                {
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "小孩"
                                    },
                                    "value": "child"
                                },
                                {
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "狗"
                                    },
                                    "value": "dog"
                                },
                                {
                                    "text": {
                                        "tag": "plain_text",
                                        "content": "猫"
                                    },
                                    "value": "cat"
                                }
                            ],
                            "selected_option": {
                                "text": {
                                    "tag": "plain_text",
                                    "content": "小孩"
                                },
                                "value": "child"
                            }
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "input",
                    "name": "member_name",
                    "placeholder": {
                        "tag": "plain_text",
                        "content": "请输入姓名/昵称"
                    },
                    "required": True
                },
                {
                    "tag": "input",
                    "name": "member_age",
                    "placeholder": {
                        "tag": "plain_text",
                        "content": "年龄（小孩）或体重（宠物，单位kg）"
                    },
                    "required": False
                },
                {
                    "tag": "input",
                    "name": "member_breed",
                    "placeholder": {
                        "tag": "plain_text",
                        "content": "品种（宠物，可选）"
                    },
                    "required": False
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "添加成员"
                            },
                            "type": "primary",
                            "value": {
                                "action": "add_family_member"
                            }
                        }
                    ]
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "💡 大人请通过邀请链接加入"
                        }
                    ]
                }
            ]
        }
    }


def family_info_card(family_data: Dict[str, Any]) -> Dict[str, Any]:
    """家庭信息展示卡片"""
    members_list = "\n".join([
        f"• {m['type_name']}: {m['name']}" + (f"（{m['age']}岁）" if m.get('age') else "") + (f"（{m['weight']}kg）" if m.get('weight') else "")
        for m in family_data.get('members', [])
    ])

    return {
        "type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🏠 {family_data['family_name']}"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": False,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**家庭ID**: {family_data['family_id']}\n**创建时间**: {family_data['created_at']}"
                            }
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**成员构成**\n大人：{family_data['adult_count']}人\n小孩：{family_data['child_count']}人\n宠物：{family_data['pet_count']}只"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**成员列表**\n{members_list}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**邀请码**: {family_data['invite_code']}\n💡 发送邀请码给家人，让他们输入\"加入家庭 {family_data['invite_code']}\"即可加入"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "生成邀请链接"
                            },
                            "type": "primary",
                            "value": {
                                "action": "generate_invite_link"
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "添加成员"
                            },
                            "type": "default",
                            "value": {
                                "action": "show_add_member_card"
                            }
                        }
                    ]
                }
            ]
        }
    }


def invite_link_card(invite_data: Dict[str, Any]) -> Dict[str, Any]:
    """邀请链接分享卡片"""
    return {
        "type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🎉 邀请家人加入"
                },
                "template": "orange"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": f"邀请链接已生成！有效期{invite_data['expires_days']}天"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**邀请链接**:\n{invite_data['invite_link']}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**邀请码**: {invite_data['invite_code']}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": "使用方式：\n1. 点击链接直接加入\n2. 或在机器人对话中输入\"加入家庭 邀请码\""
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "复制邀请码"
                            },
                            "type": "primary",
                            "value": {
                                "action": "copy_invite_code",
                                "invite_code": invite_data['invite_code']
                            }
                        }
                    ]
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"有效期至：{invite_data['expires_at']}"
                        }
                    ]
                }
            ]
        }
    }


def join_success_card(family_data: Dict[str, Any]) -> Dict[str, Any]:
    """加入家庭成功卡片"""
    return {
        "type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"✅ 成功加入 {family_data['family_name']}"
                },
                "template": "green"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"欢迎加入！你现在可以：\n• 记录购买和消耗\n• 查看家庭库存\n• 接收补货提醒"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**家庭成员**\n大人：{family_data['adult_count']}人\n小孩：{family_data['child_count']}人\n宠物：{family_data['pet_count']}只"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看家庭信息"
                            },
                            "type": "primary",
                            "value": {
                                "action": "show_family_info"
                            }
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "记录购买"
                            },
                            "type": "default",
                            "value": {
                                "action": "record_purchase"
                            }
                        }
                    ]
                }
            ]
        }
    }


__all__ = [
    'create_family_card',
    'add_family_member_card',
    'family_info_card',
    'invite_link_card',
    'join_success_card',
]