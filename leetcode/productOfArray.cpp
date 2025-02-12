/*
Given an integer array nums, return an array answer such that answer[i] is equal to the product of all the elements of nums except nums[i].
The product of any prefix or suffix of nums is guaranteed to fit in a 32-bit integer.
You must write an algorithm that runs in O(n) time and without using the division operation.

Example 1:

Input: nums = [1,2,3,4]
Output: [24,12,8,6]
Example 2:

Input: nums = [-1,1,0,-3,3]
Output: [0,0,9,0,0]
 
Constraints:

2 <= nums.length <= 105
-30 <= nums[i] <= 30
The input is generated such that answer[i] is guaranteed to fit in a 32-bit integer.
https://leetcode.com/problems/product-of-array-except-self/description/?envType=study-plan-v2&envId=leetcode-75
*/

#include<iostream>
#include<vector>
using namespace std;

class Solution {
public: 
    vector<int> productExceptSelf(vector<int> nums) {
        int n = nums.size();
        vector<int> ans(n);
        for (int i = 0, left = 1; i < n; ++i)
        {
            ans[i] = left;
            left *= nums[i];
        }
        for (int i = n - 1, right = 1; ~i; --i)
        {
            ans[i] *= right;
            right *= nums[i];
        }
        return ans;
    }
};

int main() {
    Solution sol;
    vector<int> nums = {-1, 1, 0, -3, 3};
    vector<int> ans = sol.productExceptSelf(nums);

    for (int num : ans)
    {
        cout << num << " ";
    }
    cout << endl;

    return 0;
}