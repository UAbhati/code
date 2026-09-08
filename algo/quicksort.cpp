#include<iostream>
using namespace std;

const int INSERTION_SORT_THRESHOLD = 10; 
// insertion sort is faster for <= 10 elements

int medianOfThree(int arr[], int low,int high) {
    // to make we don't reach worth condition of n^2
    int mid = low + (high-low)/2;
    if(arr[low] > arr[mid]) swap(arr[low],arr[mid]);
    if(arr[low] > arr[high]) swap(arr[low], arr[high]);
    if(arr[mid] > arr[high]) swap(arr[mid], arr[high]);
    swap(arr[mid],arr[high]);
    return arr[high];
}

int partition(int arr[], int low,int high) {
    int pivot=medianOfThree(arr, low,high);
    int i=low-1;
    for(int j=low;j<high;++j) {
        if(arr[j] < pivot) {
            i++;
            swap(arr[i],arr[j]);
        }
    }
    swap(arr[i+1],arr[high]);
    return i+1;
}

void insertSort(int arr[], int low, int high) {
    for(int i=low+1;i<=high;++i) {
        int key = arr[i], j=i-1;
        while(j>=low && arr[j]>key) {
            arr[j+1] = arr[j];
            j--;
        }
        arr[j+1] = key;
    }
}

void quickSort(int arr[], int low, int high) {
    while(low<high) {
        if(high-low +1 <INSERTION_SORT_THRESHOLD) {
            insertSort(arr, low, high);
            break;
        }
        // to make sure we have depth of log(n) for recursion
        int pivot = partition(arr, low, high);
        if(pivot-low < high-pivot) {
            quickSort(arr, low, pivot - 1);
            low = pivot+1;
        } else {
            quickSort(arr, pivot+1, high);
            high = pivot-1;
        }
    }
}

void printArray(int arr[], int size) {
    for (int i = 0; i < size; i++) 
        cout << arr[i] << " ";
    cout << endl;
}

int main() {
    int arr[] = {10, 7, 8, 9, 1, 5, 20, 15, 3, 2};
    int n = sizeof(arr) / sizeof(arr[0]);

    quickSort(arr, 0, n - 1);
    printArray(arr, n);

    return 0;
}
