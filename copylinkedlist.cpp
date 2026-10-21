
class Solution {
    public:
        Node* copyRandomList(Node* head) {
            if (!head) return nullptr;

            // Pass 1: Insert each copy after its original
            Node* curr = head;

            while (curr) {
                Node* copy = new Node(curr->val, curr->next, nullptr);
                curr->next = copy;
                curr = copy->next;
            }

            // Pass 2: Assign random pointers to copies
            curr = head;

            while (curr) {
                Node* copy = curr->next;

                if (curr->random) {
                    copy->random = curr->random->next;
                }

                curr = copy->next;
            }

            // Pass 3: Separate original and copied lists
            curr = head;
            Node* copyHead = head->next;

            while (curr) {
                Node* copy = curr->next;

                curr->next = copy->next;

                if (copy->next) {
                    copy->next = copy->next->next;
                }

                curr = curr->next;
            }

            return copyHead;
        }
    };
